"""Notificaciones: adjuntos por WhatsApp (gafete/protocolo) y aviso de cancelación de cita.

Cubre el contrato de media del helper ``notificar_whatsapp`` (texto primero, luego media
best-effort), la construcción del adjunto de protocolo, y que la cancelación de una cita produce un
mensaje de **cancelación** (no la invitación). Sin DB: se usan dobles y monkeypatch.
"""

from __future__ import annotations

from types import SimpleNamespace

from apps.mensajeria.proveedores import AdjuntoWhatsApp, ResultadoEnvio

# ── AdjuntoWhatsApp ────────────────────────────────────────────────────────────


def test_adjunto_whatsapp_b64_y_es_imagen():
    adj = AdjuntoWhatsApp(nombre_archivo="g.png", contenido=b"abc", mimetype="image/png")
    assert adj.es_imagen is True
    assert adj.b64() == "YWJj"  # base64("abc")
    pdf = AdjuntoWhatsApp(nombre_archivo="p.pdf", contenido=b"x", mimetype="application/pdf")
    assert pdf.es_imagen is False


# ── notificar_whatsapp: texto primero, media best-effort ───────────────────────


def test_notificar_whatsapp_texto_luego_media(monkeypatch):
    from apps.mensajeria import services

    llamadas = []

    def fake_enviar(telefono, cuerpo, archivo=None, *, adjunto=None, **kw):
        llamadas.append({"cuerpo": cuerpo, "adjunto": adjunto})
        return ResultadoEnvio(ok=True, proveedor="sandbox", external_id="x")

    monkeypatch.setattr(services.router, "enviar", fake_enviar)

    adjs = [
        AdjuntoWhatsApp("g.png", b"img", "image/png", caption="cap gafete"),
        AdjuntoWhatsApp("p.pdf", b"pdf", "application/pdf", caption="cap protocolo"),
    ]
    ok = services.notificar_whatsapp("8112223344", "TEXTO PRINCIPAL", adjuntos=adjs)

    assert ok is True
    # 1 texto + 2 media, en ese orden.
    assert len(llamadas) == 3
    assert llamadas[0]["adjunto"] is None and llamadas[0]["cuerpo"] == "TEXTO PRINCIPAL"
    assert llamadas[1]["adjunto"].nombre_archivo == "g.png"
    assert llamadas[1]["cuerpo"] == "cap gafete"  # el caption del adjunto
    assert llamadas[2]["adjunto"].nombre_archivo == "p.pdf"


def test_notificar_whatsapp_media_best_effort(monkeypatch):
    """Si el envío de media lanza, el texto ya se entregó y no se propaga el error."""
    from apps.mensajeria import services

    def fake_enviar(telefono, cuerpo, archivo=None, *, adjunto=None, **kw):
        if adjunto is not None:
            raise RuntimeError("media provider caído")
        return ResultadoEnvio(ok=True, proveedor="sandbox", external_id="x")

    monkeypatch.setattr(services.router, "enviar", fake_enviar)
    adjs = [AdjuntoWhatsApp("g.png", b"img", "image/png", caption="cap")]
    ok = services.notificar_whatsapp("8112223344", "texto", adjuntos=adjs)
    assert ok is True  # el texto principal fue aceptado; la media falló en silencio


def test_notificar_whatsapp_sin_telefono_no_manda(monkeypatch):
    from apps.mensajeria import services

    monkeypatch.setattr(
        services.router,
        "enviar",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no llamar")),
    )
    assert services.notificar_whatsapp("", "texto", adjuntos=[]) is False


# ── adjunto_protocolo ──────────────────────────────────────────────────────────


class _FakeArchivo:
    def __init__(self, data: bytes):
        self._data = data
        self.name = "protocolos/reglas.pdf"

    def open(self, mode="rb"):
        return self

    def read(self):
        return self._data

    def close(self):
        pass


def test_adjunto_protocolo_lee_bytes():
    from apps.mensajeria.services import adjunto_protocolo

    prot = SimpleNamespace(nombre="Reglas Casa", archivo=_FakeArchivo(b"%PDF-1.4 demo"))
    adj = adjunto_protocolo(prot, caption="cap")
    assert adj is not None
    assert adj.mimetype == "application/pdf"
    assert adj.contenido == b"%PDF-1.4 demo"
    assert adj.nombre_archivo == "protocolo-Reglas-Casa.pdf"
    assert adj.caption == "cap"


def test_adjunto_protocolo_sin_archivo_devuelve_none():
    from apps.mensajeria.services import adjunto_protocolo

    assert adjunto_protocolo(None) is None
    assert adjunto_protocolo(SimpleNamespace(nombre="X", archivo=None)) is None


# ── Cancelación de cita: mensaje de cancelación, no invitación ─────────────────


def _fake_cita(**over):
    asistentes = over.pop("asistentes", [])
    mgr = SimpleNamespace(all=lambda: list(asistentes), count=lambda: len(asistentes))
    base = dict(
        pk=1,
        tipo=1,
        tipo_cita="programada",
        nombre="Visita demo",
        fecha=None,
        hora_inicio=None,
        recinto=SimpleNamespace(nombre="Recinto X"),
        ubicacion=SimpleNamespace(nombre="Lobby"),
        punto_acceso=None,
        protocolo_id=None,
        protocolo=None,
        limite=None,
        proveedor=None,
        asistentes=mgr,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_cancelacion_asistentes_dice_cancelada(monkeypatch):
    from apps.citas import services as S

    monkeypatch.setattr(S, "_nombre_tenant", lambda cita: "Museos")
    correos, wa = [], []
    monkeypatch.setattr(S, "enviar_correo_html", lambda **k: correos.append(k))
    monkeypatch.setattr(
        "apps.mensajeria.services.notificar_whatsapp",
        lambda telefono, cuerpo, *a, **k: (wa.append(cuerpo) or True),
    )

    asis = SimpleNamespace(pk=1, nombre="Juan", email="j@x.com", telefono="8112223344")
    n = S.enviar_cancelacion_cita(_fake_cita(tipo=1, asistentes=[asis]))

    assert n == 1
    assert correos and "cancelada" in correos[0]["asunto"].lower()
    assert "CANCELADA" in correos[0]["texto_plano"]
    assert wa and "CANCELADA" in wa[0]


def test_cancelacion_proveedor_dice_cancelada(monkeypatch):
    from apps.citas import services as S

    monkeypatch.setattr(S, "_nombre_tenant", lambda cita: "Museos")
    correos, wa = [], []
    monkeypatch.setattr(S, "enviar_correo_html", lambda **k: correos.append(k))
    monkeypatch.setattr(
        "apps.mensajeria.services.notificar_whatsapp",
        lambda telefono, cuerpo, *a, **k: (wa.append(cuerpo) or True),
    )

    prov = SimpleNamespace(
        nombre_responsable="Ana",
        nombre="Prov SA",
        email_responsable="ana@prov.com",
        email=None,
        telefono="8112223344",
    )
    n = S.enviar_cancelacion_cita(_fake_cita(tipo=0, proveedor=prov))

    assert n == 1
    assert correos and "CANCELADA" in correos[0]["texto_plano"]
    assert wa and "CANCELADA" in wa[0]


# ── Alta/baja de asistentes: routing y wording ─────────────────────────────────


def test_enviar_invitacion_asistentes_solo_subconjunto(monkeypatch):
    """Agregar invitados invita SOLO a los nuevos (no reenvía a todos)."""
    from apps.citas import services as S

    capt = {}
    monkeypatch.setattr(
        S,
        "_notificar_asistentes",
        lambda cita, asistentes=None: capt.update(asistentes=asistentes) or len(asistentes or []),
    )
    a1 = SimpleNamespace(nombre="Nuevo")
    n = S.enviar_invitacion_asistentes(_fake_cita(tipo=1), [a1])
    assert n == 1
    assert capt["asistentes"] == [a1]  # subconjunto, no None (=todos)


def test_baja_asistente_dice_dado_de_baja(monkeypatch):
    from apps.citas import services as S

    monkeypatch.setattr(S, "_nombre_tenant", lambda cita: "Museos")
    correos, wa = [], []
    monkeypatch.setattr(S, "enviar_correo_html", lambda **k: correos.append(k))
    monkeypatch.setattr(
        "apps.mensajeria.services.notificar_whatsapp",
        lambda telefono, cuerpo, *a, **k: (wa.append(cuerpo) or True),
    )
    asis = SimpleNamespace(pk=1, nombre="Juan", email="j@x.com", telefono="8112223344")
    ok = S.enviar_baja_asistente(_fake_cita(tipo=1), asis)
    assert ok is True
    assert correos and "dado de baja" in correos[0]["texto_plano"].lower()
    assert wa and "dado de baja" in wa[0].lower()
