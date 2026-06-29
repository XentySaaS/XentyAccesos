#Secciones
---------------------------------------------
Usuarios
 Listado
  Nombre,correo,estatus,editar,eliminar(baja logica)
 CRUD
  Nombre,Telefono,Correo,Password,role(Administrador,editor,guardia de seguridad,recepcionista y usuario personalizado),estatus
---------------------------------------------
Proveedores
 Listado
  Resposable,Nombre,Estatus,editar ,Revision de documentos, eliminar(baja logica)
 CRUD
  Nombre de la empresa,Nombre del responsable,Correo electrónico del responsable,RFC,Razón social,Teléfono del responsable
 Modelo de negocio
  * Antes de estar activo se le envia un correo para que llene sus datos y de la empresa para que pueda darse de alta en ese step , agrega documentos y demas , y al final se crea su usuario y contraseña con los datos proporcionados.
  * En la revision de documentos se hace para poderlo poner en modo activo
---------------------------------------------
Recintos
 Listado
  Nombre del Recinto
 CRUD
  Nombre,Direccion
 Relaciones
  Puntos de acceso,Zonas,Areas Autorizadas
 CRUD Relaciones
  Punto de acceso
   Listado 
    Nombre
   CRUD PA
    Nombre,Descripcion
  Zonas
   Listado
    Nombre
   CRUD zonas
    Nombre,Descripcion
   Relaciones
    Ubicaciones
 Areas autorizadas
  Listado
   Nombre
  CRUD
   Nombre , descripcion



#Reglas
* algunos registros requieren de bajas logicas para no perder informacion
* Se ocupa el registro de acciones para todos los usuarios del sistema (Historial de cambios)