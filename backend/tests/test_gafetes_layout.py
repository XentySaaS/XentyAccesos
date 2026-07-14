"""Gafete de acceso: las secciones con texto envolvente no se empalman (alto dinámico).

No se puede asertar el layout pixel a pixel, pero sí que el contenido más grande (zona en 2 líneas,
punto de acceso y nombre de evento largos) reserva MÁS alto que un caso mínimo — que es justo lo que
evita el empalme. ``componer_gafete`` es puro (no toca BD): se pasa un token cualquiera.
"""

from __future__ import annotations

from io import BytesIO


def _alto(**kw) -> int:
    from PIL import Image

    from apps.gafetes.services import componer_gafete

    png = componer_gafete(
        token="token-de-prueba",
        nombre_invitado=kw.pop("nombre_invitado", "Ana"),
        fecha_evento="15 Jul 2026",
        vigencia_hasta="17 Jul 2026",
        **kw,
    )
    return Image.open(BytesIO(png)).height


def test_gafete_alto_crece_con_el_contenido():
    corto = _alto(zona="VIP", nombre_evento="Corto")
    largo = _alto(
        zona="ZONA NORTE",  # 2 palabras → 2 líneas
        punto_de_acceso="Acceso principal por la puerta grande de Reforma",
        nombre_evento="Montaje de obra y logística de proveedores externos del recinto",
        nombre_invitado="Juan Pablo Hernández de la Torre y Mendoza",
    )
    # El caso grande reserva más alto (secciones dinámicas): así no se encima con la siguiente.
    assert largo > corto


def test_gafete_devuelve_png_valido():
    from PIL import Image

    from apps.gafetes.services import componer_gafete

    png = componer_gafete(
        token="t",
        nombre_invitado="Manuel",
        recinto="MUSEO 1",
        zona="ZONA NORTE",
        punto_de_acceso="Punto 1",
        nombre_evento="Montaje de obra",
        fecha_evento="15 Jul 2026",
        vigencia_hasta="17 Jul 2026",
    )
    img = Image.open(BytesIO(png))
    assert img.format == "PNG"
    assert img.width == 340 and img.height > 800
