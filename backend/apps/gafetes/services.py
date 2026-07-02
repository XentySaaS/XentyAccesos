"""Emisión y verificación de QR de acceso **inviolable** (REMEDIATION §C3).

Reemplaza el AES-128-ECB con clave fija en git del origen por un token **cifrado y autenticado con
Fernet** (AES-128-CBC + HMAC) que embebe ``id|contexto|tipo`` + ``jti`` único + ``exp`` (vigencia)
+ ``tenant``. Sin la ``SECRET_KEY_FERNET`` del servidor el QR no se puede forjar ni alterar.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import qrcode
from cryptography.fernet import InvalidToken

from common.crypto import get_fernet

# Códigos de contexto que van en el QR.
TIPO_EVENTO   = "01"
TIPO_PARKING  = "02"
TIPO_CITA     = "03"


class QRInvalido(Exception):
    """QR ausente, alterado, expirado o de otro tenant."""


def emitir_qr(*, id: int, tipo: str, tenant: str, exp_epoch: float, contexto: str = "") -> str:
    """Emite un token QR firmado/cifrado con identificador único y vigencia."""
    payload = {
        "id": id, "tipo": tipo, "ctx": contexto or tipo,
        "jti": uuid.uuid4().hex, "exp": int(exp_epoch), "tenant": tenant,
    }
    return get_fernet().encrypt(json.dumps(payload).encode()).decode()


def verificar_qr(token: str, *, tenant: str | None = None) -> dict:
    """Descifra y valida el QR. Lanza ``QRInvalido`` si no es válido, expiró o es de otro tenant."""
    if not token:
        raise QRInvalido("QR ausente.")
    try:
        data = json.loads(get_fernet().decrypt(token.encode()).decode())
    except (InvalidToken, ValueError):
        raise QRInvalido("QR no válido (firma o formato).")
    if data.get("exp", 0) < time.time():
        raise QRInvalido("QR expirado.")
    if tenant is not None and data.get("tenant") != tenant:
        raise QRInvalido("QR de otro tenant.")
    return data


def generar_png(token: str) -> bytes:
    """Genera un PNG simple con el QR del token (sin diseño de gafete)."""
    from io import BytesIO
    img = qrcode.make(token)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Diseño «Estadio Clásico» (1a) — Design handoff Xenty Accesos ──────────────
#
#  Estructura (top → bottom):
#  1. Cabecera blanca   · XENTY ACCESOS + título recinto | ícono Xenty
#  2. Barra accent verde  (gradiente #00B248 → #00E676)
#  3. Foto del portador   (centrada, rounded, sobre fondo de rayas navy)
#  4. Zona + QR           (texto Bebas Neue izq. | QR der., sobre rayas)
#  5. Separador           (1 px semi-transparente)
#  6. Sección info blanca · nombre, evento, sector·dot, vigencia
#  7. Footer oscuro       · texto legal

_STATIC_FONTS = Path(__file__).parent.parent.parent / "static" / "fonts"
_STATIC       = Path(__file__).parent.parent.parent / "static"

# Paleta
_C_NAVY    = (7,   17,  31)   # #07111F — fondo principal
_C_STRIPE  = (12,  30,  52)   # #0C1E34 — raya alternada
_C_DARKEST = (3,   10,  19)   # #030A13 — footer
_C_GREEN   = (0,   200, 83)   # #00C853 — acento
_C_GREEN_D = (0,   178, 72)   # #00B248
_C_GREEN_L = (0,   230, 118)  # #00E676
_C_ORANGE  = (255, 109, 0)    # #FF6D00 — estacionamiento
_C_WHITE   = (255, 255, 255)

# Colores de zona (accent bar + dot sector)
_ZONA_ACCENT: dict[str, tuple[int, int, int]] = {
    "CANCHA":   (0,   200, 83),
    "VIP":      (255, 215, 0),
    "PRENSA":   (156, 39,  176),
    "STAFF":    (255, 109, 0),
    "GENERAL":  (33,  150, 243),
}


def _accent_zona(zona: str) -> tuple[int, int, int]:
    z = zona.upper()
    for k, c in _ZONA_ACCENT.items():
        if k in z:
            return c
    return _C_GREEN


# ── Fuentes ──────────────────────────────────────────────────────────────────

def _try_font(paths: list, size: int):
    from PIL import ImageFont
    for p in paths:
        try:
            return ImageFont.truetype(str(p), size)
        except OSError:
            continue
    return ImageFont.load_default()


def _inter(size: int, bold: bool = False):
    w = "Bold" if bold else "Regular"
    return _try_font([
        _STATIC_FONTS / f"Inter-{w}.ttf",
        f"/usr/share/fonts/truetype/inter/Inter-{w}.ttf",
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ], size)


def _bebas(size: int):
    """Bebas Neue condensed (display). Paquete Debian instala .otf en opentype/."""
    return _try_font([
        _STATIC_FONTS / "BebasNeue-Regular.ttf",
        "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Regular.otf",
        "/usr/share/fonts/truetype/bebas-neue/BebasNeue-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ], size)


# ── Primitivas de dibujo ─────────────────────────────────────────────────────

def _grad_h(draw, x0: int, y0: int, x1: int, y1: int,
            c0: tuple, c1: tuple) -> None:
    """Gradiente horizontal sólido entre dos colores RGB."""
    w = x1 - x0
    if w <= 0:
        return
    for i in range(w):
        t = i / max(w - 1, 1)
        draw.line(
            [(x0 + i, y0), (x0 + i, y1 - 1)],
            fill=(
                round(c0[0] + (c1[0] - c0[0]) * t),
                round(c0[1] + (c1[1] - c0[1]) * t),
                round(c0[2] + (c1[2] - c0[2]) * t),
                255,
            ),
        )


def _rayas_bg(img, x0: int, y0: int, x1: int, y1: int) -> None:
    """Fondo de rayas diagonales navy (replica CSS repeating-linear-gradient(-45deg))."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(*_C_NAVY, 255))
    S = 18   # semi-periodo de la raya
    h = y1 - y0
    w = x1 - x0
    for start in range(-(h + S * 2), w + h + S * 2, S * 2):
        pts = [
            (x0 + start,         y1 - 1),
            (x0 + start + h,     y0),
            (x0 + start + h + S, y0),
            (x0 + start + S,     y1 - 1),
        ]
        d.polygon(pts, fill=(*_C_STRIPE, 255))


def _xenty_icon(draw, x: int, y: int, size: int = 44) -> None:
    """Ícono Xenty: cuadro oscuro redondeado + círculo verde + checkmark."""
    draw.rounded_rectangle(
        [x, y, x + size, y + size],
        radius=round(size * 0.20),
        fill=(*_C_NAVY, 255),
    )
    cx, cy = x + size // 2, y + size // 2
    r  = round(size * 0.296)
    sw = max(1, round(size * 0.042))
    for i in range(sw + 1):
        draw.ellipse(
            [cx - r + i, cy - r + i, cx + r - i, cy + r - i],
            outline=(*_C_GREEN, 255),
        )
    # Checkmark M15 22 l5.5 5.5 8.5-11 (coordenadas en viewBox 44px)
    s  = size / 44
    p1 = (round(x + 15   * s), round(y + 22   * s))
    p2 = (round(x + 20.5 * s), round(y + 27.5 * s))
    p3 = (round(x + 29   * s), round(y + 16.5 * s))
    lw = max(2, round(size * 0.052))
    draw.line([p1, p2], fill=(*_C_GREEN, 255), width=lw)
    draw.line([p2, p3], fill=(*_C_GREEN, 255), width=lw)


def _silhouette(draw, px: int, py: int, pw: int, ph: int) -> None:
    """Placeholder cuando no hay foto: ícono de persona centrado."""
    f  = (*_C_WHITE, 90)
    cx = px + pw // 2
    # cabeza
    rh = round(pw * 0.21)
    hy = py + round(ph * 0.16)
    draw.ellipse([cx - rh, hy, cx + rh, hy + rh * 2], fill=f)
    # cuerpo (óvalo centrado en la parte baja)
    brx  = round(pw * 0.38)
    bry2 = round(ph * 0.27)
    by   = py + round(ph * 0.84)
    draw.ellipse([cx - brx, by - bry2, cx + brx, by + bry2], fill=f)


def _wrap_text(draw, text: str, x: int, y: int, max_w: int,
               font, fill, leading: int = 10) -> None:
    """Dibuja texto con salto de línea automático."""
    words = text.split()
    line  = ""
    for word in words:
        trial = (line + " " + word).strip()
        bb = draw.textbbox((0, 0), trial, font=font)
        if bb[2] - bb[0] <= max_w:
            line = trial
        else:
            if line:
                draw.text((x, y), line, font=font, fill=fill)
                y += leading
            line = word
    if line:
        draw.text((x, y), line, font=font, fill=fill)


def _text_ls(draw, text: str, x: int, y: int, font, fill, ls: int = 2) -> None:
    """Dibuja texto carácter a carácter con letter-spacing manual."""
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bb = draw.textbbox((0, 0), ch, font=font)
        x += (bb[2] - bb[0]) + ls


def _text_ls_center(draw, text: str, cx: int, y: int, font, fill, ls: int = 2) -> None:
    """Igual que _text_ls pero centrado en cx."""
    total = sum(
        draw.textbbox((0, 0), c, font=font)[2] - draw.textbbox((0, 0), c, font=font)[0] + ls
        for c in text
    ) - ls
    _text_ls(draw, text, cx - total // 2, y, font, fill, ls)


def _parse_lineas(lineas: list[str]) -> tuple[str, str, str, str]:
    """Extrae (evento_n, zona_n, acceso_n, fecha_n) de las líneas del gafete."""
    evento_n = lineas[0] if lineas else ""
    zona_n = acceso_n = fecha_n = ""
    for ln in lineas[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            ks = k.strip().lower()
            if "zona" in ks:
                zona_n = v.strip().upper()
            elif "acceso" in ks:
                acceso_n = v.strip()
            elif not any(c.isdigit() for c in k.strip()):
                pass  # etiqueta desconocida sin dígitos → ignorar
            else:
                fecha_n = ln.strip()
        else:
            fecha_n = ln.strip()
    return evento_n, zona_n, acceso_n, fecha_n


def _render_card(
    *,
    W: int,
    H: int,
    RADIO: int,
    header_fn,        # callable(draw) → dibuja el interior del header
    bar_colors: tuple,  # (c_start, c_end) o None para verde
    stripe_y0: int,
    stripe_y1: int,
    body_fn,          # callable(img, draw) → dibuja el área de rayas
    sep_y: int,
    info_fn,          # callable(draw) → dibuja la sección info blanca
    INFO_H: int,
    FOOT_H: int,
    footer_text: str,
) -> bytes:
    """Renderiza la estructura común de tarjeta y devuelve PNG bytes."""
    from io import BytesIO
    from PIL import Image, ImageDraw

    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base navy (toda la tarjeta)
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=(*_C_NAVY, 255))

    # Rayas diagonales (sección media)
    _rayas_bg(img, 0, stripe_y0, W, stripe_y1)

    # Cabecera blanca
    HEADER_H = stripe_y0 - (bar_colors[2] if bar_colors else 5)  # altura barra
    BAR_H    = bar_colors[2] if bar_colors else 5
    HEADER_H = stripe_y0 - BAR_H
    draw.rectangle([0, 0, W, HEADER_H], fill=(*_C_WHITE, 255))
    header_fn(draw)

    # Barra gradiente
    c0, c1 = bar_colors[:2]
    _grad_h(draw, 0, HEADER_H, W, stripe_y0, c0, c1)

    # Contenido del área de rayas
    body_fn(img, draw)

    # Separador
    draw.line([(20, sep_y), (W - 20, sep_y)], fill=(*_C_WHITE, 23), width=1)

    # Info blanca
    info_y = sep_y + 1
    draw.rectangle([0, info_y, W, info_y + INFO_H], fill=(*_C_WHITE, 255))
    info_fn(draw, info_y)

    # Footer oscuro
    foot_y = info_y + INFO_H
    draw.rectangle([0, foot_y, W, H], fill=(*_C_DARKEST, 255))
    f_leg = _inter(7)
    _wrap_text(draw, footer_text, 20, foot_y + 9, W - 40, f_leg, (*_C_WHITE, 51))

    # Máscara de esquinas redondeadas
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=255)
    img.putalpha(mask)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Gafete de acceso — v2 «Premium Dark · Acento Dorado» ─────────────────────

def componer_gafete(
    *,
    token: str,
    nombre_invitado: str,
    recinto: str = "",
    zona: str = "GENERAL",
    punto_de_acceso: str = "",
    nombre_evento: str = "",
    fecha_evento: str = "",
    hora_evento: str = "",
    vigencia_hasta: str = "",
    hora_vigencia: str = "",
    foto_bytes: bytes | None = None,
    codigo_acceso: str = "",
    empresa: str = "XENTY ACCESOS",
    accent_color: str | None = None,
    # Etiquetas sobreescribibles (para reusar el diseño en citas)
    label_zona: str = "ZONA",
    label_evento: str = "NOMBRE DEL EVENTO",
    label_fecha: str = "FECHA DEL EVENTO",
) -> bytes:
    """Diseño Premium Dark con acento dorado.

    Secciones: barra dorada | header recinto | foto+zona | evento | fechas | invitado | QR | footer.
    """
    from io import BytesIO
    from PIL import Image, ImageDraw

    W     = 340
    RADIO = 20
    PAD   = 18

    # Accent por zona (dorado por defecto)
    _ZONE_COLORS: dict[str, tuple[int, int, int]] = {
        "VIP":     (255, 215,   0),
        "CANCHA":  (  0, 200,  83),
        "GENERAL": (  0, 200,  83),
        "PRENSA":  (156,  39, 176),
        "STAFF":   (255, 109,   0),
        "PALCO":   (255, 215,   0),
    }
    if accent_color:
        h = accent_color.lstrip("#")
        AC: tuple[int, int, int] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    else:
        zkey = zona.upper().split()[0] if zona else ""
        AC = next((v for k, v in _ZONE_COLORS.items() if k in zkey), (255, 215, 0))

    GOLD   = (255, 215,   0)
    GOLD_D = (139, 100,   0)
    GOLD_M = (255, 162,   0)
    DEEP   = (  9,   9,  16)
    WHITE  = (255, 255, 255)

    # Helpers locales
    def _ls(draw, text, x, y, font, fill, ls=2):
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            bb = draw.textbbox((0, 0), ch, font=font)
            x += (bb[2] - bb[0]) + ls

    def _ls_center(draw, text, cx, y, font, fill, ls=2):
        total = sum(
            draw.textbbox((0, 0), c, font=font)[2]
            - draw.textbbox((0, 0), c, font=font)[0] + ls
            for c in text
        ) - ls
        _ls(draw, text, cx - total // 2, y, font, fill, ls)

    def _grad3(draw, y0, y1, ca, cb, cc):
        half = W // 2
        for i in range(half):
            t = i / max(half - 1, 1)
            c = tuple(round(ca[j] + (cb[j] - ca[j]) * t) for j in range(3))
            draw.line([(i, y0), (i, y1)], fill=(*c, 255))
        for i in range(half, W):
            t = (i - half) / max(W - half - 1, 1)
            c = tuple(round(cb[j] + (cc[j] - cb[j]) * t) for j in range(3))
            draw.line([(i, y0), (i, y1)], fill=(*c, 255))

    def _gold_line(draw, y):
        draw.line([(0, y), (W - 1, y)], fill=(*GOLD, 18))

    # Bebas Neue para zona — fuente más grande cuando no hay foto (ancho completo)
    z_len  = len(zona)
    if foto_bytes:
        z_size = 44 if z_len <= 10 else (36 if z_len <= 15 else 30)
    else:
        z_size = 58 if z_len <= 10 else (50 if z_len <= 15 else 40)
    f_zona = _bebas(z_size)

    PHOTO_W   = 90
    PHOTO_H_I = 132

    BAR_H   = 5
    HDR_H   = 62
    PZ_H    = (16 + PHOTO_H_I + 16) if foto_bytes else 114  # 164 con foto, 114 sin foto
    EVT_H   = 84
    DT_H    = 62
    GN_H    = 100
    QR_H    = 190
    FT_H    = 33
    H = BAR_H + HDR_H + PZ_H + EVT_H + DT_H + GN_H + QR_H + FT_H

    img  = Image.new("RGBA", (W, H), (*DEEP, 255))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=(*DEEP, 255))

    # ── 1. Barra dorada ───────────────────────────────────────────
    _grad3(draw, 0, BAR_H - 1, GOLD_D, GOLD, GOLD_M)

    # ── 2. Header ─────────────────────────────────────────────────
    y0 = BAR_H
    draw.line([(0, y0 + HDR_H - 1), (W - 1, y0 + HDR_H - 1)], fill=(*GOLD, 26))
    _ls(draw, "XENTY ACCESOS · RECINTO", PAD, y0 + 14,
        _inter(7, bold=True), (*AC, 102), ls=2)
    rec_str  = (recinto or empresa).upper()
    f_rec    = _inter(12, bold=True) if len(rec_str) > 40 else _inter(14, bold=True)
    _wrap_text(draw, rec_str, PAD, y0 + 30, W - PAD - 52, f_rec, (*WHITE, 255), leading=18)
    # Logo Xenty (blanco sobre fondo oscuro)
    _logo_path = _STATIC / "xenty-white.png"
    if _logo_path.exists():
        from PIL import Image as _PIL_Image
        _logo = _PIL_Image.open(_logo_path).convert("RGBA")
        _logo_h = 22
        _logo_w = int(_logo.width * _logo_h / _logo.height)
        _logo   = _logo.resize((_logo_w, _logo_h), _PIL_Image.LANCZOS)
        _lx = W - PAD - _logo_w
        _ly = y0 + (HDR_H - _logo_h) // 2
        img.paste(_logo, (_lx, _ly), _logo)

    # ── 3. Foto + Zona ────────────────────────────────────────────
    y1 = y0 + HDR_H
    py = y1 + 16

    if foto_bytes:
        # Con foto: recuadro a la izquierda, zona a la derecha
        px = PAD
        draw.rounded_rectangle([px, py, px + PHOTO_W, py + PHOTO_H_I], radius=10,
                                fill=(18, 26, 46, 255), outline=(*AC, 70), width=1)
        try:
            fimg = Image.open(BytesIO(foto_bytes)).convert("RGBA")
            tgt  = PHOTO_W / PHOTO_H_I
            src  = fimg.width / fimg.height
            if src > tgt:
                nw = int(fimg.height * tgt)
                fimg = fimg.crop(((fimg.width - nw) // 2, 0, (fimg.width + nw) // 2, fimg.height))
            else:
                nh = int(fimg.width / tgt)
                fimg = fimg.crop((0, (fimg.height - nh) // 2, fimg.width, (fimg.height + nh) // 2))
            fimg  = fimg.resize((PHOTO_W, PHOTO_H_I), Image.LANCZOS)
            fmask = Image.new("L", (PHOTO_W, PHOTO_H_I), 0)
            ImageDraw.Draw(fmask).rounded_rectangle(
                [0, 0, PHOTO_W - 1, PHOTO_H_I - 1], radius=10, fill=255)
            img.paste(fimg, (px, py), fmask)
        except Exception:  # noqa: BLE001
            _silhouette(draw, px, py, PHOTO_W, PHOTO_H_I)
        zx         = px + PHOTO_W + 14
        zone_col_w = W - PAD - zx
    else:
        # Sin foto: zona ocupa todo el ancho
        zx         = PAD
        zone_col_w = W - PAD * 2

    _ls(draw, label_zona, zx, py, _inter(7, bold=True), (*AC, 102), ls=2)

    z_display = zona.upper()
    for wd in z_display.split():
        bw = draw.textbbox((0, 0), wd, font=f_zona)
        if (bw[2] - bw[0]) > zone_col_w:
            f_zona = _bebas(max(round(z_size * zone_col_w / max(bw[2] - bw[0], 1)), 22))

    z_cur_y = py + 10 + 3
    for wd in z_display.split():
        draw.text((zx, z_cur_y), wd, font=f_zona, fill=(*WHITE, 255))
        bw = draw.textbbox((0, 0), wd, font=f_zona)
        z_cur_y += round((bw[3] - bw[1]) * 0.88)

    # Divisor dorado con fade
    div_y = z_cur_y + 11
    for xi in range(zone_col_w):
        t = xi / max(zone_col_w - 1, 1)
        draw.line([(zx + xi, div_y), (zx + xi, div_y + 1)],
                  fill=(*GOLD, round(255 * (1 - t ** 1.2))))

    if punto_de_acceso:
        _ls(draw, "PUNTO DE ACCESO", zx, div_y + 10,
            _inter(7, bold=True), (*AC, 102), ls=2)
        _wrap_text(draw, punto_de_acceso, zx, div_y + 22, zone_col_w,
                   _inter(11, bold=True), (*WHITE, 255), leading=15)

    # ── 4. Nombre del evento ──────────────────────────────────────
    y2 = y1 + PZ_H
    _gold_line(draw, y2)
    _gold_line(draw, y2 + EVT_H - 1)
    _ls(draw, label_evento, PAD, y2 + 12, _inter(7, bold=True), (*AC, 102), ls=2)
    _wrap_text(draw, nombre_evento, PAD, y2 + 27, W - PAD * 2,
               _inter(13, bold=True), (*WHITE, 255), leading=17)

    # ── 5. Fechas ─────────────────────────────────────────────────
    y3   = y2 + EVT_H
    half = (W - 1) // 2
    _gold_line(draw, y3 + DT_H - 1)
    _ls(draw, label_fecha, PAD, y3 + 12, _inter(7, bold=True), (*AC, 102), ls=2)
    draw.text((PAD, y3 + 26), fecha_evento, font=_inter(13, bold=True), fill=(*WHITE, 255))
    if hora_evento:
        draw.text((PAD, y3 + 44), hora_evento, font=_inter(9), fill=(*WHITE, 77))
    draw.line([(half, y3 + 10), (half, y3 + DT_H - 10)], fill=(*GOLD, 18))
    rx = half + PAD
    _ls(draw, "VIGENCIA HASTA", rx, y3 + 12, _inter(7, bold=True), (*AC, 102), ls=2)
    draw.text((rx, y3 + 26), vigencia_hasta, font=_inter(13, bold=True), fill=(*WHITE, 255))
    if hora_vigencia:
        draw.text((rx, y3 + 44), hora_vigencia, font=_inter(9), fill=(*WHITE, 77))

    # ── 6. Nombre del invitado ────────────────────────────────────
    y4 = y3 + DT_H
    _gold_line(draw, y4 + GN_H - 1)
    _ls(draw, "NOMBRE DEL INVITADO", PAD, y4 + 13, _inter(7, bold=True), (*AC, 102), ls=2)
    _wrap_text(draw, nombre_invitado, PAD, y4 + 27, W - PAD * 2,
               _inter(17, bold=True), (*WHITE, 255), leading=22)

    # ── 7. QR ─────────────────────────────────────────────────────
    y5      = y4 + GN_H
    QR_BOX  = 108
    QR_PAD_I = 8
    QR_SIZE = QR_BOX - QR_PAD_I * 2
    qr_bx   = (W - QR_BOX) // 2
    qr_by   = y5 + 15
    draw.rounded_rectangle([qr_bx, qr_by, qr_bx + QR_BOX, qr_by + QR_BOX],
                            radius=12, fill=(*WHITE, 255))
    qr_img = (
        qrcode.make(token).convert("RGBA")
        .resize((QR_SIZE, QR_SIZE), Image.NEAREST)
    )
    img.paste(qr_img, (qr_bx + QR_PAD_I, qr_by + QR_PAD_I))
    _ls_center(draw, "ESCANEAR PARA VALIDAR", W // 2, qr_by + QR_BOX + 8,
               _inter(7, bold=True), (*AC, 102), ls=2)
    if codigo_acceso:
        f_code = _inter(8)
        cb     = draw.textbbox((0, 0), codigo_acceso, font=f_code)
        draw.text(
            ((W - (cb[2] - cb[0])) // 2, qr_by + QR_BOX + 8 + 10 + 8),
            codigo_acceso, font=f_code, fill=(*WHITE, 51),
        )

    # ── 8. Footer ─────────────────────────────────────────────────
    y6 = y5 + QR_H
    _gold_line(draw, y6)
    draw.rectangle([0, y6, W - 1, H - 1], fill=(*GOLD, 8))
    _wrap_text(
        draw,
        "Todos los accesos son intransferibles. "
        "Xenty Accesos · Sistema de Control de Acceso",
        PAD, y6 + 9, W - PAD * 2, _inter(7), (*WHITE, 41), leading=10,
    )

    # Máscara de esquinas redondeadas
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=255)
    img.putalpha(mask)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Gafete de estacionamiento — v2 «Premium Dark · Acento Dorado» ────────────

def componer_gafete_estacionamiento(
    *,
    token: str,
    nombre_empresa: str,
    recinto: str,
    evento: str,
    parking: str = "",
    cajon: str = "",
    vigencia: str = "",
    zona: str = "GENERAL",
    empresa: str = "XENTY ACCESOS",
) -> bytes:
    """Diseño Premium Dark para pases de estacionamiento.

    Secciones: barra dorada | header título+logo | proveedor | cajón+QR | info | footer.
    Sin foto de portador. Sin grilla.
    """
    from io import BytesIO
    from PIL import Image, ImageDraw

    W     = 340
    RADIO = 20
    PAD   = 18

    GOLD   = (255, 215,   0)
    GOLD_D = (139, 100,   0)
    GOLD_M = (255, 162,   0)
    DEEP   = (  9,   9,  16)
    WHITE  = (255, 255, 255)

    _ZONE_COLORS: dict[str, tuple[int, int, int]] = {
        "GENERAL":   (255, 215,   0),
        "VIP":       (255, 215,   0),
        "STAFF":     (255, 109,   0),
        "PRENSA":    (156,  39, 176),
        "PROVEEDOR": ( 33, 150, 243),
    }
    zkey = zona.upper().split()[0] if zona else "GENERAL"
    AC = next((v for k, v in _ZONE_COLORS.items() if k in zkey), GOLD)

    cajon_display = (cajon or parking or "C-1").upper()

    def _cajon_size(c: str) -> int:
        if len(c) <= 3: return 94
        if len(c) <= 4: return 78
        if len(c) <= 6: return 60
        return 48

    f_caj_size = _cajon_size(cajon_display)
    f_caj      = _bebas(f_caj_size)

    # Helpers locales
    def _ls(draw, text, x, y, font, fill, ls=2):
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            bb = draw.textbbox((0, 0), ch, font=font)
            x += (bb[2] - bb[0]) + ls

    def _ls_center(draw, text, cx, y, font, fill, ls=2):
        total = sum(
            draw.textbbox((0, 0), c, font=font)[2]
            - draw.textbbox((0, 0), c, font=font)[0] + ls
            for c in text
        ) - ls
        _ls(draw, text, cx - total // 2, y, font, fill, ls)

    def _grad3(draw, y0, y1, ca, cb, cc):
        half = W // 2
        for i in range(half):
            t = i / max(half - 1, 1)
            c = tuple(round(ca[j] + (cb[j] - ca[j]) * t) for j in range(3))
            draw.line([(i, y0), (i, y1)], fill=(*c, 255))
        for i in range(half, W):
            t = (i - half) / max(W - half - 1, 1)
            c = tuple(round(cb[j] + (cc[j] - cb[j]) * t) for j in range(3))
            draw.line([(i, y0), (i, y1)], fill=(*c, 255))

    def _sep(draw, y):
        draw.line([(0, y), (W - 1, y)], fill=(*GOLD, 18))

    BAR_H  = 5
    HDR_H  = 92
    PROV_H = 83
    CAJ_H  = 130
    INFO_H = 88
    FOOT_H = 48
    H = BAR_H + HDR_H + PROV_H + CAJ_H + INFO_H + FOOT_H  # 446

    img  = Image.new("RGBA", (W, H), (*DEEP, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=(*DEEP, 255))

    # ── 1. Barra dorada ───────────────────────────────────────────
    _grad3(draw, 0, BAR_H - 1, GOLD_D, GOLD, GOLD_M)

    # ── 2. Header ─────────────────────────────────────────────────
    y0 = BAR_H
    _sep(draw, y0 + HDR_H - 1)
    _ls(draw, "XENTY ACCESOS", PAD, y0 + 15, _inter(7, bold=True), (*GOLD, 102), ls=2)
    f_title = _inter(20, bold=True)
    draw.text((PAD, y0 + 30), "PASE DE",          font=f_title, fill=(*WHITE, 255))
    draw.text((PAD, y0 + 54), "ESTACIONAMIENTO",  font=f_title, fill=(*WHITE, 255))
    _logo_path = _STATIC / "xenty-white.png"
    if _logo_path.exists():
        from PIL import Image as _PIL_Image
        _logo   = _PIL_Image.open(_logo_path).convert("RGBA")
        _logo_h = 22
        _logo_w = int(_logo.width * _logo_h / _logo.height)
        _logo   = _logo.resize((_logo_w, _logo_h), _PIL_Image.LANCZOS)
        img.paste(_logo, (W - PAD - _logo_w, y0 + 20), _logo)

    # ── 3. Proveedor ──────────────────────────────────────────────
    y1 = y0 + HDR_H
    _sep(draw, y1 + PROV_H - 1)
    ix = PAD
    iy = y1 + (PROV_H - 52) // 2
    draw.rounded_rectangle([ix, iy, ix + 52, iy + 52], radius=12,
                            fill=(*GOLD, 18), outline=(*GOLD, 51), width=1)
    # Ícono de auto estilizado centrado en el cuadro
    cx_i = ix + 26
    cy_i = iy + 26
    draw.rounded_rectangle([cx_i - 15, cy_i - 2, cx_i + 15, cy_i + 9], radius=3,
                            fill=(*GOLD, 140))
    draw.polygon([
        (cx_i - 12, cy_i - 2), (cx_i - 10, cy_i - 7),
        (cx_i + 10, cy_i - 7), (cx_i + 12, cy_i - 2),
    ], fill=(*GOLD, 140))
    draw.ellipse([cx_i - 12, cy_i + 6, cx_i - 6, cy_i + 12], fill=(*GOLD, 179))
    draw.ellipse([cx_i +  6, cy_i + 6, cx_i + 12, cy_i + 12], fill=(*GOLD, 179))

    tx = ix + 52 + 14
    _ls(draw, "PROVEEDOR", tx, iy + 4, _inter(7, bold=True), (*GOLD, 102), ls=2)
    f_emp_hdr = _inter(14, bold=True)
    emp_hdr   = nombre_empresa.upper()
    max_emp_w = W - PAD - tx - 4
    while len(emp_hdr) > 2:
        eb = draw.textbbox((0, 0), emp_hdr, font=f_emp_hdr)
        if (eb[2] - eb[0]) <= max_emp_w:
            break
        emp_hdr = emp_hdr[:-1]
    if emp_hdr != nombre_empresa.upper():
        emp_hdr = emp_hdr[:-1] + "…"
    draw.text((tx, iy + 20), emp_hdr, font=f_emp_hdr, fill=(*WHITE, 255))

    # ── 4. Cajón + QR ─────────────────────────────────────────────
    y2 = y1 + PROV_H
    _sep(draw, y2 + CAJ_H - 1)
    QR_BOX   = 100
    QR_PAD_I = 8
    QR_SIZE  = QR_BOX - QR_PAD_I * 2
    qr_bx    = W - PAD - QR_BOX
    qr_by    = y2 + (CAJ_H - QR_BOX) // 2
    draw.rounded_rectangle([qr_bx, qr_by, qr_bx + QR_BOX, qr_by + QR_BOX],
                            radius=11, fill=(*WHITE, 255))
    qr_img = (
        qrcode.make(token).convert("RGBA")
        .resize((QR_SIZE, QR_SIZE), Image.NEAREST)
    )
    img.paste(qr_img, (qr_bx + QR_PAD_I, qr_by + QR_PAD_I))
    _ls_center(draw, "ESCANEAR", qr_bx + QR_BOX // 2, qr_by + QR_BOX + 6,
               _inter(7, bold=True), (*GOLD, 102), ls=2)

    _ls(draw, "CAJÓN / LOTE", PAD, y2 + 14, _inter(7, bold=True), (*GOLD, 102), ls=2)
    max_caj_w = qr_bx - PAD - 8
    bb = draw.textbbox((0, 0), cajon_display, font=f_caj)
    if (bb[2] - bb[0]) > max_caj_w:
        f_caj = _bebas(max(round(f_caj_size * max_caj_w / max(bb[2] - bb[0], 1)), 36))
        bb    = draw.textbbox((0, 0), cajon_display, font=f_caj)
    caj_y = qr_by + QR_BOX - (bb[3] - bb[1])
    draw.text((PAD, caj_y), cajon_display, font=f_caj, fill=(*AC, 255))

    # ── 5. Info del evento ────────────────────────────────────────
    y3 = y2 + CAJ_H
    _sep(draw, y3 + INFO_H - 1)
    emp_info = nombre_empresa
    f_emp_info = _inter(18, bold=True)
    eb2 = draw.textbbox((0, 0), emp_info, font=f_emp_info)
    if (eb2[2] - eb2[0]) > W - PAD * 2:
        emp_info = (emp_info[:22] + "…") if len(emp_info) > 23 else emp_info
    draw.text((PAD, y3 + 14), emp_info, font=f_emp_info, fill=(*WHITE, 255))
    ev_str = f"Evento: {evento}"
    if len(ev_str) > 48:
        ev_str = ev_str[:46] + "…"
    draw.text((PAD, y3 + 44), ev_str, font=_inter(10), fill=(*WHITE, 102))
    ry = y3 + 64
    draw.ellipse([PAD, ry + 1, PAD + 8, ry + 9], fill=(*AC, 255))
    draw.text((PAD + 12, ry), zona.upper(), font=_inter(10, bold=True), fill=(*WHITE, 255))
    if vigencia:
        vig_str = f"VIGENCIA: {vigencia[:10]}"
        vb      = draw.textbbox((0, 0), vig_str, font=_inter(10))
        draw.text((W - PAD - (vb[2] - vb[0]), ry), vig_str,
                  font=_inter(10), fill=(*WHITE, 97))

    # ── 6. Footer ─────────────────────────────────────────────────
    y4 = y3 + INFO_H
    draw.rectangle([0, y4, W - 1, H - 1], fill=(*GOLD, 8))
    _sep(draw, y4)
    _wrap_text(
        draw,
        "Los pases de estacionamiento son intransferibles. "
        "Válido únicamente para el evento y cajón indicados. "
        "Xenty Accesos no se responsabiliza por el uso no autorizado.",
        PAD, y4 + 9, W - PAD * 2, _inter(7), (*WHITE, 41), leading=10,
    )

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=255)
    img.putalpha(mask)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
