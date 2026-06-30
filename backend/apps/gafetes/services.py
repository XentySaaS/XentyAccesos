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
    """Silueta de persona (placeholder cuando no hay foto)."""
    f  = (*_C_WHITE, 51)
    cx = px + pw // 2
    rh = round(pw * 0.24)
    hy = py + round(ph * 0.09)
    draw.ellipse([cx - rh, hy, cx + rh, hy + rh * 2], fill=f)
    bry  = round(ph * 0.83)
    brx  = round(pw * 0.43)
    bry2 = round(ph * 0.28)
    draw.ellipse(
        [cx - brx, py + bry - bry2, cx + brx, py + bry + bry2],
        fill=f,
    )


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

    # Bebas Neue para zona
    z_len  = len(zona)
    z_size = 44 if z_len <= 10 else (36 if z_len <= 15 else 30)
    f_zona = _bebas(z_size)

    PHOTO_W   = 90
    PHOTO_H_I = 132

    BAR_H   = 5
    HDR_H   = 62
    PZ_H    = 16 + PHOTO_H_I + 16   # 164
    EVT_H   = 84
    DT_H    = 62
    GN_H    = 100
    QR_H    = 190
    FT_H    = 33
    H = BAR_H + HDR_H + PZ_H + EVT_H + DT_H + GN_H + QR_H + FT_H  # 740... will recompute
    H = 5 + 62 + 164 + 84 + 62 + 100 + 190 + 33   # 700

    img  = Image.new("RGBA", (W, H), (*DEEP, 255))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIO, fill=(*DEEP, 255))

    # Grilla dorada sutil
    for xi in range(0, W, 26):
        draw.line([(xi, 0), (xi, H - 1)], fill=(*GOLD, 6))
    for yi in range(0, H, 26):
        draw.line([(0, yi), (W - 1, yi)], fill=(*GOLD, 6))

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
    # Ícono
    ix, iy = W - PAD - 40, y0 + 12
    draw.rounded_rectangle([ix, iy, ix + 40, iy + 40], radius=8, fill=(*GOLD, 18))
    draw.rounded_rectangle([ix, iy, ix + 40, iy + 40], radius=8, outline=(*GOLD, 56), width=1)
    icx, icy = ix + 20, iy + 20
    draw.ellipse([icx - 10, icy - 10, icx + 10, icy + 10], outline=(*GOLD, 71), width=1)
    s  = 40 / 44
    lw = max(2, round(40 * 0.055))
    draw.line([(round(ix + 13 * s), round(iy + 20 * s)),
               (round(ix + 18.5 * s), round(iy + 25.5 * s))], fill=(*GOLD, 255), width=lw)
    draw.line([(round(ix + 18.5 * s), round(iy + 25.5 * s)),
               (round(ix + 27 * s), round(iy + 14.5 * s))], fill=(*GOLD, 255), width=lw)

    # ── 3. Foto + Zona ────────────────────────────────────────────
    y1   = y0 + HDR_H
    px   = PAD
    py   = y1 + 16
    draw.rounded_rectangle([px, py, px + PHOTO_W, py + PHOTO_H_I], radius=10,
                            fill=(*WHITE, 10), outline=(*AC, 46), width=1)
    if foto_bytes:
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
    else:
        _silhouette(draw, px, py, PHOTO_W, PHOTO_H_I)

    zx        = px + PHOTO_W + 14
    zone_col_w = W - PAD - zx

    _ls(draw, "ZONA", zx, py, _inter(7, bold=True), (*AC, 102), ls=2)

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
    _ls(draw, "NOMBRE DEL EVENTO", PAD, y2 + 12, _inter(7, bold=True), (*AC, 102), ls=2)
    _wrap_text(draw, nombre_evento, PAD, y2 + 27, W - PAD * 2,
               _inter(13, bold=True), (*WHITE, 255), leading=17)

    # ── 5. Fechas ─────────────────────────────────────────────────
    y3   = y2 + EVT_H
    half = (W - 1) // 2
    _gold_line(draw, y3 + DT_H - 1)
    _ls(draw, "FECHA DEL EVENTO", PAD, y3 + 12, _inter(7, bold=True), (*AC, 102), ls=2)
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


# ── Gafete de estacionamiento ─────────────────────────────────────────────────

def componer_gafete_estacionamiento(
    *,
    token: str,
    nombre_empresa: str,
    recinto: str,
    evento: str,
    parking: str = "",
    cajon: str = "",
    vigencia: str = "",
    empresa: str = "XENTY ACCESO",
) -> bytes:
    """Adaptación del diseño 1a para pases de estacionamiento (sin foto, acento naranja)."""
    from io import BytesIO
    from PIL import Image, ImageDraw

    W     = 340
    RADIO = 20

    # Texto que va en el "nombre de zona" (izquierda grande)
    zona_display = (cajon or parking or "C-1")[:8].upper()
    sector_label = (parking or "ESTACIONAMIENTO")[:20].upper()

    HEADER_H = 80
    BAR_H    = 5
    ICON_H   = 120   # área del ícono P + nombre empresa
    ZONE_H   = 134
    SEP_H    = 1
    INFO_H   = 112
    FOOT_H   = 56
    H = HEADER_H + BAR_H + ICON_H + ZONE_H + SEP_H + INFO_H + FOOT_H  # 508

    stripe_y0 = HEADER_H + BAR_H
    stripe_y1 = stripe_y0 + ICON_H + ZONE_H
    sep_y     = stripe_y1

    # ── Cabecera ──────────────────────────────────────────────────
    def _header(draw):
        f_lbl = _inter(8, bold=True)
        f_rec = _inter(22, bold=True)
        draw.text((20, 10), "XENTY ACCESOS", font=f_lbl, fill=(*_C_NAVY, 115))
        draw.text((20, 26), "PASE DE",          font=f_rec, fill=(*_C_NAVY, 255))
        draw.text((20, 52), "ESTACIONAMIENTO",  font=f_rec, fill=(*_C_NAVY, 255))
        _xenty_icon(draw, W - 20 - 44, 12, 44)

    # ── Ícono P + empresa + zona + QR ────────────────────────────
    def _body(img, draw):
        # Círculo con «P»
        cx_p  = W // 2
        r_p   = 38
        icon_center_y = stripe_y0 + ICON_H // 2 - 10
        draw.ellipse(
            [cx_p - r_p, icon_center_y - r_p, cx_p + r_p, icon_center_y + r_p],
            fill=(*_C_WHITE, 18), outline=(*_C_WHITE, 40), width=2,
        )
        f_p  = _bebas(58)
        pb   = draw.textbbox((0, 0), "P", font=f_p)
        draw.text(
            (cx_p - (pb[2] - pb[0]) // 2, icon_center_y - (pb[3] - pb[1]) // 2 - 2),
            "P", font=f_p, fill=(*_C_WHITE, 200),
        )
        # Nombre de empresa bajo el círculo
        f_co   = _inter(11, bold=True)
        co_str = nombre_empresa.upper()[:22]
        cb     = draw.textbbox((0, 0), co_str, font=f_co)
        draw.text(
            ((W - (cb[2] - cb[0])) // 2, icon_center_y + r_p + 8),
            co_str, font=f_co, fill=(*_C_WHITE, 200),
        )

        # QR (derecha, alineado al fondo)
        QR_SIZE = 78
        QR_PAD  = 7
        QR_TOT  = QR_SIZE + QR_PAD * 2
        qx = W - 20 - QR_TOT
        qy = stripe_y1 - 20 - QR_TOT

        draw.rounded_rectangle(
            [qx, qy, qx + QR_TOT, qy + QR_TOT],
            radius=9, fill=(*_C_WHITE, 255),
        )
        qr_img = (
            qrcode.make(token).convert("RGBA")
            .resize((QR_SIZE, QR_SIZE), Image.NEAREST)
        )
        img.paste(qr_img, (qx + QR_PAD, qy + QR_PAD))

        f_scan = _inter(8, bold=True)
        sb = draw.textbbox((0, 0), "ESCANEAR", font=f_scan)
        draw.text(
            (qx + (QR_TOT - (sb[2] - sb[0])) // 2, qy + QR_TOT + 3),
            "ESCANEAR", font=f_scan, fill=(*_C_WHITE, 77),
        )

        # Número de cajón / lote (izquierda, grande)
        f_lbl_z = _inter(8, bold=True)
        f_caj   = _bebas(92)

        max_w = qx - 20 - 8
        bb    = draw.textbbox((0, 0), zona_display, font=f_caj)
        if (bb[2] - bb[0]) > max_w:
            f_caj = _bebas(max(round(92 * max_w / max(bb[2] - bb[0], 1)), 42))

        bb    = draw.textbbox((0, 0), zona_display, font=f_caj)
        caj_h = bb[3] - bb[1]
        caj_y = qy + QR_TOT - caj_h + 2
        draw.text((20, caj_y - 12), "CAJON / LOTE", font=f_lbl_z, fill=(*_C_WHITE, 82))
        draw.text((20, caj_y),      zona_display,   font=f_caj,   fill=(*_C_ORANGE, 255))

    # ── Info blanca ───────────────────────────────────────────────
    def _info(draw, iy):
        f_nm = _inter(26, bold=True)
        f_ev = _inter(11)
        f_se = _inter(10, bold=True)
        f_vg = _inter(10)

        emp = (nombre_empresa[:21] + "…") if len(nombre_empresa) > 23 else nombre_empresa
        draw.text((20, iy + 14), emp, font=f_nm, fill=(*_C_NAVY, 255))

        ev = f"Evento: {evento}"
        if len(ev) > 46:
            ev = ev[:44] + "…"
        draw.text((20, iy + 54), ev, font=f_ev, fill=(*_C_NAVY, 122))

        ry = iy + 78
        draw.ellipse([20, ry + 1, 27, ry + 8], fill=(*_C_ORANGE, 255))
        draw.text((31, ry), sector_label, font=f_se, fill=(*_C_NAVY, 255))
        if vigencia:
            vig_str = f"VIGENCIA: {vigencia[:10]}"
            vb = draw.textbbox((0, 0), vig_str, font=f_vg)
            draw.text(
                (W - 20 - (vb[2] - vb[0]), ry),
                vig_str, font=f_vg, fill=(*_C_NAVY, 107),
            )

    return _render_card(
        W=W, H=H, RADIO=RADIO,
        header_fn=_header,
        bar_colors=((255, 100, 0), (255, 180, 0), BAR_H),
        stripe_y0=stripe_y0,
        stripe_y1=stripe_y1,
        body_fn=_body,
        sep_y=sep_y,
        info_fn=_info,
        INFO_H=INFO_H,
        FOOT_H=FOOT_H,
        footer_text=(
            "Los pases de estacionamiento son intransferibles. Válido únicamente para el "
            "evento y cajón indicados. Xenty Accesos no se responsabiliza por el uso no autorizado."
        ),
    )
