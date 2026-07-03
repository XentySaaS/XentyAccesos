"""OCR de INE: AWS Textract con algoritmo de parser de líneas portado del origen.

Estrategia:
  1. detect_document_text → parser de líneas (port fiel del PHP ReadIneOCRController,
     con corrección de deuda: validaSeccionINE es real, no vacía).
  2. analyze_id (Textract nativo) como complemento para rellenar campos que el parser
     no encontró — en particular útil cuando el scan viene recortado.

Si no hay credenciales AWS se usa SandboxOCR (dev/test, datos deterministas).
El llamador cifra ine_data al guardarlo; aquí no se loguea PII.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from django.conf import settings

# ─── Normalización ─────────────────────────────────────────────────────────────


def _norm(text: str) -> str:
    """Quita acentos y normaliza a mayúsculas (port del str_replace de acentos del PHP)."""
    nfkd = unicodedata.normalize("NFKD", text)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.upper()


# ─── Expresiones regulares ──────────────────────────────────────────────────────

_HEADERS_INE = re.compile(
    r"^(INSTITUTO\s*NACIONAL\s*ELECTORAL|MEXICO|MÉXICO|CREDENCIAL\s*PARA\s*VOTAR"
    r"|UNIDOS|DEPARTMENT|INSTITUTO|ELECTORAL|NACIONAL|CREDENCIAL|PARA|VOTAR)$",
    re.I,
)

# CURP: patrón oficial (18 caracteres)
_RE_CURP = re.compile(
    r"\b(?:[A-Z][AEIOUX][A-Z]{2})(?:[0-9]{2})(?:[0-9]{2})(?:[0-9]{2})"
    r"(?:[HM])(?:[A-Z]{2})(?:[B-DF-HJ-NP-TV-Z]{3})(?:[0-9A-Z])(?:[0-9])\b"
)

# Clave de elector: 18 caracteres con estructura específica
_RE_CLAVE = re.compile(
    r"\b(?:[A-Z][B-DF-HJ-NP-TV-Z]){3}[0-9]{2}(?:0[1-9]|1[0-2])"
    r"(?:[1-2][0-9]|0[1-9]|3[0-1])(?:0[1-9]|[1-2][0-9]|3[0-2]|88|87)[HM][0-9]{3}\b"
)

_RE_SECCION = re.compile(r"^\d{1,4}$")
_RE_ANIO_REG = re.compile(r"^\d{4}\s\d{2}$")  # e.g. "2020 20"


# ─── Validadores (port fiel del PHP, sin la validación hueca validaSeccionINE) ──


def _es_sexo(v: str) -> bool:
    return bool(re.match(r"^[HM]$", v.strip()))


def _es_curp(v: str) -> bool:
    return bool(_RE_CURP.search(v))


def _es_clave_elector(v: str) -> bool:
    return bool(_RE_CLAVE.search(v))


def _es_fecha(v: str) -> bool:
    try:
        datetime.strptime(v.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return False


def _es_vigencia(v: str) -> bool:
    """YYYY-YYYY o YYYY - YYYY; ambos años razonables y el primero menor."""
    clean = v.replace(" ", "")
    partes = clean.split("-")
    if len(partes) == 2:
        try:
            a, b = int(partes[0]), int(partes[1])
            return 1980 <= a <= 2100 and 1980 <= b <= 2100 and a < b
        except ValueError:
            return False
    return False


def _es_anio_registro(v: str) -> bool:
    """Formato '2020 20' (año de registro + dígito de versión de la INE)."""
    return bool(_RE_ANIO_REG.match(v.strip()))


def validar_seccion(seccion: str | None) -> bool:
    """Sección electoral: 1-4 dígitos > 0.  (reemplaza validaSeccionINE que siempre retornaba True)."""
    if not seccion:
        return False
    s = str(seccion).strip()
    return bool(_RE_SECCION.match(s)) and int(s) > 0


# ─── Definición de campos a extraer ─────────────────────────────────────────────
# Estructura idéntica al PHP:
#   search=True  → buscar el valor validándolo con fn()
#   search=False → tomar las próximas `lines` líneas después de ini_val
#   lines=0, search=False → valor inline en la misma línea (p.ej. CLAVE DE ELECTOR)

_CAMPOS_DEF: list[dict[str, Any]] = [
    {"key": "NOMBRE", "lines": 3, "ini_val": 1, "search": False, "fn": None},
    {"key": "SEXO", "lines": 0, "ini_val": 0, "search": True, "fn": _es_sexo},
    {"key": "DOMICILIO", "lines": 3, "ini_val": 0, "search": False, "fn": None},
    {"key": "CLAVE DE ELECTOR", "lines": 0, "ini_val": 0, "search": False, "fn": _es_clave_elector},
    {"key": "CURP", "lines": 1, "ini_val": 1, "search": True, "fn": _es_curp},
    {"key": "ANO DE REGISTRO", "lines": 1, "ini_val": 1, "search": True, "fn": _es_anio_registro},
    {"key": "FECHA DE NACIMIENTO", "lines": 1, "ini_val": 2, "search": True, "fn": _es_fecha},
    {"key": "SECCION", "lines": 1, "ini_val": 2, "search": True, "fn": validar_seccion},
    {"key": "VIGENCIA", "lines": 1, "ini_val": 2, "search": True, "fn": _es_vigencia},
]


# ─── Algoritmo principal (port de identificarFormulario + extractIne del PHP) ──


def _identificar_formulario(lines_raw: list[str]) -> list[dict[str, Any]]:
    """
    Port de ReadIneOCRController::identificarFormulario().

    Diferencias con el origen:
    - Trabaja con copias; no muta la lista de campos en-place.
    - validaSeccionINE es real (no vacía).
    - Retorna la lista de campos con pos, value e items (items se usa para separar nombre/apellidos).
    - Devuelve [] si no se identificaron ≥5 campos (igual que el PHP que retornaba error).
    """
    # Filtrar líneas puramente en minúsculas (igual que el PHP)
    lines: list[str] = [ln for ln in lines_raw if not ln.islower()]

    # Detectar formato viejo (INEs 2008, 2013, 2014) — busca "ESTADO" en líneas
    is_old = any("ESTADO" in _norm(ln) for ln in lines)

    # Inicializar estado de cada campo
    campos: list[dict[str, Any]] = [
        {**c, "pos": -1, "value": "", "pos_real": -1, "items": []} for c in _CAMPOS_DEF
    ]

    # ── Primera pasada: localizar la posición de cada etiqueta ──────────────────
    for x, line in enumerate(lines):
        if _HEADERS_INE.match(line.strip()):
            continue
        norm_line = _norm(line)
        for campo in campos:
            if campo["pos"] >= 0:
                continue  # ya localizado
            key_n = _norm(campo["key"])
            m = re.match(rf"^{re.escape(key_n)}\s+(.+)$", norm_line)
            if m or (key_n in norm_line):
                campo["pos"] = x
                # Valor inline (mismo renglón que la etiqueta)
                if campo["lines"] == 0 and m:
                    campo["value"] = m.group(1).strip()
                    campo["pos_real"] = x

    # Rechazar si menos de 5 campos identificados (mismo umbral que el PHP)
    if sum(1 for c in campos if c["pos"] >= 0) < 5:
        return []

    # ── Segunda pasada: extraer valores ─────────────────────────────────────────
    postem_anterior = 0

    for idx, campo in enumerate(campos):
        pos = campo["pos"]
        if pos < 0 or campo["value"]:
            continue

        nl = campo["lines"]
        iv = campo["ini_val"]
        fn = campo["fn"]
        ini = pos + iv

        if campo["search"] and fn:
            validado = False

            # Caso especial formato viejo: SECCION y VIGENCIA están inline con ESTADO/MUNICIPIO/LOCALIDAD
            if is_old and campo["key"] in ("SECCION", "VIGENCIA"):
                norm_line = _norm(lines[pos])
                palabras = norm_line.split()
                key_n = _norm(campo["key"])
                try:
                    cam = next(i for i, w in enumerate(palabras) if w == key_n)
                except StopIteration:
                    cam = None
                if cam is not None and cam + 1 < len(palabras):
                    valor = palabras[cam + 1]
                    if campo["key"] == "SECCION" and fn(valor):
                        campo["value"] = valor
                        validado = True
                    elif campo["key"] == "VIGENCIA":
                        try:
                            em = next(i for i, w in enumerate(palabras) if w == "EMISION")
                            if em + 1 < len(palabras):
                                rango = f"{palabras[em + 1]}-{valor}"
                                if fn(rango):
                                    campo["value"] = rango
                                    validado = True
                        except StopIteration:
                            pass

            for x in range(ini, len(lines)):
                if validado:
                    break
                norm_line = _norm(lines[x])
                palabras = norm_line.split()

                # Solución 1: primera palabra que valide (port directo del PHP)
                for palabra in palabras:
                    if fn(palabra):
                        campo["value"] = palabra
                        campo["pos_real"] = x
                        postem_anterior = x
                        validado = True
                        break
                if validado:
                    break

                # Solución 2: línea que contiene la etiqueta → extraer el resto
                key_n = _norm(campo["key"])
                if key_n in norm_line:
                    linea_sin_key = norm_line.replace(key_n, "").strip()
                    if linea_sin_key and fn(linea_sin_key):
                        if postem_anterior == x and idx > 0:
                            prev = campos[idx - 1]
                            linea_sin_key = linea_sin_key.replace(_norm(prev["key"]), "")
                            linea_sin_key = linea_sin_key.replace(
                                _norm(str(prev["value"])), ""
                            ).strip()
                        campo["value"] = linea_sin_key
                        campo["pos_real"] = x
                        postem_anterior = x
                        validado = True
                        continue

                # Solución 3: línea sin la etiqueta (etiqueta ya consumida)
                linea_sin_key = norm_line.replace(_norm(campo["key"]), "").strip()
                if linea_sin_key and fn(linea_sin_key):
                    if postem_anterior == x and idx > 0:
                        prev = campos[idx - 1]
                        linea_sin_key = linea_sin_key.replace(_norm(prev["key"]), "")
                        linea_sin_key = linea_sin_key.replace(_norm(str(prev["value"])), "").strip()
                    campo["value"] = linea_sin_key
                    campo["pos_real"] = x
                    postem_anterior = x
                    validado = True

            if campo["key"] == "VIGENCIA":
                campo["value"] = campo["value"].replace(" ", "")

        else:
            # Modo multi-línea: tomar las próximas `nl` líneas
            if nl < 1:
                continue

            temp = lines[:]
            adjusted_ini = ini

            # Formato viejo con NOMBRE: filtrar SEXO, fechas y líneas "H"/"M" intercaladas
            if is_old and campo["key"] == "NOMBRE":
                temp = [
                    ln
                    for ln in temp
                    if not re.search(r"(SEXO|FECHA\s*DE\s*NACIMIENTO)", _norm(ln))
                    and not _es_fecha(ln.strip())
                    and not _es_sexo(ln.strip())
                ]
                adjusted_ini = max(0, adjusted_ini - 1)

            items: list[str] = []
            for i in range(nl):
                line_idx = adjusted_ini + i
                if line_idx >= len(temp):
                    break
                items.append(temp[line_idx].strip())

            campo["value"] = " ".join(items).strip()
            campo["items"] = items

    return campos


def _campos_a_datos_ine(campos: list[dict[str, Any]]) -> dict[str, str]:
    """
    Convierte la lista de campos a la estructura de la API:
      nombre, apellidos, curp, fecha_nacimiento, sexo, domicilio, seccion, numero.

    NOMBRE en la INE tiene 3 líneas:
      items[0] = apellido paterno
      items[1] = apellido materno
      items[2] = nombre(s)
    """
    datos: dict[str, str] = {}

    for campo in campos:
        v = campo.get("value", "").strip()
        if not v:
            continue
        key = campo["key"]

        if key == "NOMBRE":
            items = campo.get("items", [])
            if len(items) >= 3:
                datos["apellidos"] = f"{items[0]} {items[1]}".strip()
                datos["nombre"] = items[2]
            elif len(items) == 2:
                datos["apellidos"] = items[0]
                datos["nombre"] = items[1]
            else:
                datos["nombre"] = v
        elif key == "SEXO":
            datos["sexo"] = v
        elif key == "DOMICILIO":
            datos["domicilio"] = v
        elif key == "CLAVE DE ELECTOR":
            datos["numero"] = v
        elif key == "CURP":
            datos["curp"] = v.upper()
        elif key == "FECHA DE NACIMIENTO":
            datos["fecha_nacimiento"] = v
        elif key == "SECCION":
            if validar_seccion(v):
                datos["seccion"] = v
        elif key == "VIGENCIA":
            datos["vigencia"] = v

    return datos


# ─── Backends ───────────────────────────────────────────────────────────────────


class SandboxOCR:
    """Dev/test: no llama a AWS; devuelve campos de ejemplo deterministas."""

    def extraer_ine(self, imagen_bytes: bytes) -> dict:
        return {
            "nombre": "JUAN",
            "apellidos": "PÉREZ LÓPEZ",
            "curp": "PELJ900101HDFRPN09",
            "fecha_nacimiento": "01/01/1990",
            "sexo": "H",
            "domicilio": "CALLE FALSA 123, COLONIA EJEMPLO",
            "seccion": "1234",
            "numero": "PELJ900101HDFRPN09",
        }


class TextractOCR:
    """
    Producción: detect_document_text + parser de líneas (mismo algoritmo que el PHP de origen).

    Complementa con analyze_id para campos que el parser no encontró (FIRST_NAME/LAST_NAME
    cuando el scan viene muy recortado y no muestra las etiquetas de label).
    """

    # Mapeo de campos de analyze_id a los de la API (complemento)
    _ANALYZE_ID_MAP = {
        "FIRST_NAME": "nombre",
        "LAST_NAME": "apellidos",
        "DATE_OF_BIRTH": "fecha_nacimiento",
        "DOCUMENT_NUMBER": "numero",
        "ADDRESS": "domicilio",
        "CURP": "curp",
        "PERSONAL_NUMBER": "curp",
    }

    def extraer_ine(self, imagen_bytes: bytes) -> dict:
        import boto3

        cliente = boto3.client(
            "textract",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        # ── Paso 1: parser de líneas (algoritmo portado del PHP) ─────────────────
        resp_texto = cliente.detect_document_text(Document={"Bytes": imagen_bytes})
        lines = [b["Text"] for b in resp_texto.get("Blocks", []) if b.get("BlockType") == "LINE"]
        campos = _identificar_formulario(lines)
        datos = _campos_a_datos_ine(campos) if campos else {}

        # ── Paso 2: analyze_id como complemento para campos faltantes ────────────
        campos_faltantes = {
            k
            for k in ("nombre", "apellidos", "curp", "fecha_nacimiento", "domicilio", "numero")
            if not datos.get(k)
        }
        if campos_faltantes:
            try:
                resp_id = cliente.analyze_id(DocumentPages=[{"Bytes": imagen_bytes}])
                for doc in resp_id.get("IdentityDocuments", []):
                    for field in doc.get("IdentityDocumentFields", []):
                        clave = field.get("Type", {}).get("Text")
                        valor = (field.get("ValueDetection", {}).get("Text") or "").strip()
                        destino = self._ANALYZE_ID_MAP.get(clave)
                        if destino and destino in campos_faltantes and valor:
                            datos[destino] = valor
                            campos_faltantes.discard(destino)
            except Exception:
                pass  # analyze_id falla en algunos formatos viejos; el parser ya hizo lo posible

        return datos


def obtener_ocr():
    """Selecciona el backend OCR según haya credenciales AWS configuradas."""
    if getattr(settings, "AWS_ACCESS_KEY_ID", None) and getattr(
        settings, "AWS_SECRET_ACCESS_KEY", None
    ):
        return TextractOCR()
    return SandboxOCR()
