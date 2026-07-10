"""Textos por defecto de los documentos legales, sembrados al crear un tenant.

Son plantillas **base y editables**: el tenant nace con un aviso de privacidad y unos términos
válidos desde el día uno (LFPDPPP art. 15-16), y el administrador puede publicar versiones nuevas
desde el panel de Privacidad (v2, v3…). El texto se guarda en claro (``DocumentoLegal.texto``),
en **texto plano** — sin HTML — porque la UI lo edita/muestra como tal.
"""

from __future__ import annotations

from .models import DocumentoLegal

# Nota que encabeza ambas plantillas: deja explícito que hay que revisarlas con el área legal.
_NOTA_PLANTILLA = (
    "[PLANTILLA BASE — Este documento es un texto inicial generado automáticamente. "
    "Revísalo y adáptalo con tu área legal antes de publicarlo como definitivo.]"
)


def aviso_privacidad_default(nombre_tenant: str) -> str:
    return f"""{_NOTA_PLANTILLA}

AVISO DE PRIVACIDAD

En cumplimiento de la Ley Federal de Protección de Datos Personales en Posesión de los Particulares
(LFPDPPP), su Reglamento y los Lineamientos del Aviso de Privacidad, {nombre_tenant} ("el
Responsable") pone a su disposición el presente Aviso de Privacidad.

1. RESPONSABLE DEL TRATAMIENTO
{nombre_tenant} es responsable del uso, protección y tratamiento de sus datos personales conforme a
lo aquí descrito.

2. DATOS PERSONALES QUE SE RECABAN
Para las finalidades señaladas, podremos recabar datos de identificación y contacto (nombre,
domicilio, teléfono, correo electrónico), datos de identificación oficial (INE, CURP, RFC), datos
laborales (empresa, puesto) y, en su caso, la fotografía y documentación necesaria para el control
de acceso a las instalaciones. No se recaban datos personales sensibles salvo aviso expreso.

3. FINALIDADES DEL TRATAMIENTO
Finalidades primarias (necesarias para el servicio): (a) identificar y autorizar el acceso de
personas y proveedores a los recintos; (b) generar y validar gafetes y credenciales de acceso;
(c) gestionar eventos, citas y bitácoras de acceso; (d) dar cumplimiento a obligaciones legales,
fiscales y de seguridad. Finalidades secundarias (no necesarias): envío de comunicaciones sobre el
servicio. Usted puede oponerse a las finalidades secundarias en cualquier momento.

4. TRANSFERENCIAS
Sus datos no serán transferidos a terceros sin su consentimiento, salvo las excepciones previstas en
el artículo 37 de la LFPDPPP (por ejemplo, requerimientos de autoridad competente).

5. DERECHOS ARCO
Usted tiene derecho a Acceder, Rectificar y Cancelar sus datos personales, así como a Oponerse a su
tratamiento o revocar el consentimiento otorgado (derechos ARCO). Para ejercerlos, presente su
solicitud al Responsable a través de los medios de contacto que {nombre_tenant} tenga habilitados.
Su solicitud será atendida en un plazo máximo de 20 días naturales.

6. MEDIDAS DE SEGURIDAD
El Responsable implementa medidas de seguridad administrativas, técnicas y físicas para proteger sus
datos personales contra daño, pérdida, alteración, destrucción o uso, acceso o tratamiento no
autorizados. La información de identificación se conserva cifrada.

7. USO DE TECNOLOGÍAS DE RASTREO
La plataforma utiliza mecanismos técnicos estrictamente necesarios para la operación del servicio
(sesión y seguridad). No se emplean con fines publicitarios.

8. CAMBIOS AL AVISO DE PRIVACIDAD
El presente aviso puede sufrir modificaciones. Toda actualización se pondrá a su disposición a través
de la plataforma, indicando la versión vigente.
"""


def terminos_condiciones_default(nombre_tenant: str) -> str:
    return f"""{_NOTA_PLANTILLA}

TÉRMINOS Y CONDICIONES DE USO

Los presentes Términos y Condiciones regulan el acceso y uso de la plataforma de control de accesos
operada por {nombre_tenant} ("la Plataforma"). Al registrarse y utilizar la Plataforma, usted acepta
quedar obligado por estos Términos.

1. ACEPTACIÓN
El uso de la Plataforma implica la aceptación plena y sin reservas de estos Términos. Si no está de
acuerdo, deberá abstenerse de utilizarla.

2. DESCRIPCIÓN DEL SERVICIO
La Plataforma permite gestionar el acceso de personas, empleados y proveedores a los recintos de
{nombre_tenant}, incluyendo eventos, citas, credenciales con código QR, documentación y bitácoras.

3. REGISTRO Y CUENTA
Usted es responsable de la veracidad de la información que proporcione y de mantener la
confidencialidad de sus credenciales de acceso. Cualquier actividad realizada con su cuenta será de
su responsabilidad. Notifique de inmediato cualquier uso no autorizado.

4. OBLIGACIONES DEL USUARIO Y DEL PROVEEDOR
El usuario y, en su caso, la empresa proveedora se obligan a: (a) proporcionar información y
documentación veraz y vigente (por ejemplo, REPSE, SUA y demás documentos que resulten aplicables);
(b) mantener actualizada la plantilla de su personal; (c) respetar las políticas de seguridad y
acceso del recinto; (d) usar la Plataforma conforme a la ley y a estos Términos.

5. DOCUMENTACIÓN Y CUMPLIMIENTO
{nombre_tenant} podrá validar la documentación y el cumplimiento fiscal de los proveedores conforme a
la normatividad aplicable (incluida la verificación del artículo 69-B del CFF). El incumplimiento
podrá restringir el acceso.

6. PROPIEDAD INTELECTUAL
Los contenidos, marcas y software de la Plataforma son propiedad de sus respectivos titulares. No se
otorga ninguna licencia distinta de la necesaria para el uso del servicio.

7. LIMITACIÓN DE RESPONSABILIDAD
La Plataforma se ofrece "tal cual". {nombre_tenant} no será responsable por daños derivados del mal
uso del servicio, de la información proporcionada por los usuarios, o de causas de fuerza mayor.

8. VIGENCIA Y TERMINACIÓN
{nombre_tenant} podrá suspender o cancelar el acceso ante el incumplimiento de estos Términos, sin
perjuicio de las acciones legales que correspondan.

9. MODIFICACIONES
Estos Términos pueden actualizarse. La versión vigente estará siempre disponible en la Plataforma.

10. LEY APLICABLE Y JURISDICCIÓN
Estos Términos se rigen por la legislación de los Estados Unidos Mexicanos. Para cualquier
controversia, las partes se someten a los tribunales competentes del domicilio de {nombre_tenant}.
"""


_DEFAULTS = {
    DocumentoLegal.Tipo.AVISO_PRIVACIDAD: aviso_privacidad_default,
    DocumentoLegal.Tipo.TERMINOS: terminos_condiciones_default,
}


def sembrar_documentos_legales(nombre_tenant: str) -> int:
    """Crea la v1 de cada documento legal si aún no existe. Idempotente; devuelve cuántos creó.

    Debe llamarse **dentro del schema del tenant** (``schema_context``). No sobreescribe documentos
    ya publicados: si un tipo ya tiene alguna versión, se respeta.
    """
    creados = 0
    for tipo, generar in _DEFAULTS.items():
        if not DocumentoLegal.objects.filter(tipo=tipo).exists():
            DocumentoLegal.objects.create(tipo=tipo, texto=generar(nombre_tenant).strip(), version=1)
            creados += 1
    return creados
