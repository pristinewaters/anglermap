# AnglerMap — Arquitectura del ecosistema

**Estado:** definición funcional y arquitectura de producto  
**Ámbito:** plataforma AnglerMap, con piloto inicial en Río del Medio  
**Principio rector:** una sola plataforma, una base geoespacial compartida y experiencias diferenciadas por perfil.

## 1. Visión del producto

AnglerMap no es solamente una aplicación cartográfica ni un sistema de reservas. Es una plataforma que conecta descubrimiento de lugares de pesca, administración territorial y operación turística mediante una infraestructura geográfica y transaccional común.

La cartografía es la fuente compartida de contexto. Los perfiles acceden a distintas capacidades, permisos y vistas sobre los mismos cuerpos de agua, predios, sectores y accesos.

## 2. Tres pilares funcionales

### 2.1 Administrador de territorio

Objetivo: permitir que propietarios, administradores o entidades responsables habiliten actividad turística de pesca y obtengan ingresos complementarios sin desatender su actividad principal.

Capacidades:
- Incorporar y administrar uno o más territorios y cuerpos de agua.
- Revisar información hidrográfica y predial disponible.
- Delimitar sectores de uso turístico, accesos, puntos de entrada y salida.
- Definir temporadas, días habilitados, cupos, tarifas y reglas.
- Abrir, cerrar o bloquear sectores y fechas.
- Recibir y resolver solicitudes de pescadores y operadores.
- Configurar aprobación manual o confirmación automática bajo reglas.
- Gestionar acuerdos comerciales con operadores.
- Crear usuarios del equipo y asignar permisos por función y territorio.
- Consultar calendario, ocupación, ingresos, cancelaciones y reportes.
- Registrar incidencias, entradas y salidas.

El diseño debe reducir al mínimo la carga administrativa: vistas claras, valores predeterminados, automatización de tareas repetitivas y alertas solo cuando requieren intervención.

### 2.2 Operador turístico

Objetivo: facilitar la relación comercial entre operadores y administradores territoriales.

Capacidades:
- Explorar territorios y cuerpos de agua.
- Consultar los acuerdos y sectores para los que tiene autorización.
- Solicitar fechas, sectores y cupos para sus clientes.
- Administrar grupos y datos de los pescadores.
- Consultar disponibilidad, condiciones, estados y órdenes de pago.
- Mantener historial de solicitudes, reservas y operaciones.
- Gestionar solicitudes recurrentes conforme a sus acuerdos.

Un operador con convenio vigente debe disponer de un flujo directo para territorios y sectores previamente acordados. No debe repetir el proceso de descubrimiento o negociación en cada reserva.

### 2.3 Pescador recreativo

Objetivo: descubrir lugares de pesca y solicitar acceso a sectores administrados desde la experiencia cartográfica de AnglerMap.

Capacidades:
- Explorar mapas y cuerpos de agua.
- Consultar información disponible sobre sectores, especies, temporadas y condiciones.
- Identificar si un sector está administrado y si admite solicitudes.
- Consultar accesos autorizados, reglas, tarifas y disponibilidad publicable.
- Registrar a cada integrante del grupo y sus datos de licencia o pasapescadores.
- Solicitar acceso, pagar cuando corresponda y recibir la autorización.
- Consultar reservas, comprobantes e instrucciones de ingreso y salida.

La información sensible del predio, datos privados del administrador y detalles operativos no destinados al público deben permanecer protegidos por permisos.

## 3. Infraestructura transversal: cartografía y datos

Los tres pilares utilizan una única base geoespacial lógica. No se deben construir mapas independientes para cada perfil.

Capas y entidades principales:
- Hidrografía: ríos, esteros, lagos, lagunas y otros cuerpos de agua.
- Predios y unidades territoriales, sujetos a fuente, precisión y permisos de publicación.
- Territorios administrados y relación entre administrador y territorio.
- Sectores de pesca, geometrías, límites y estado operativo.
- Accesos, portones, estacionamientos, puntos de encuentro y rutas autorizadas.
- Puntos de entrada y salida.
- Zonas restringidas, cierres y áreas de protección.
- Información pesquera, ambiental y de servicios, con procedencia y fecha de actualización.

Regla crítica: la geometría hidrográfica o predial de referencia no equivale por sí sola a autorización de acceso. Los límites turísticos, accesos y condiciones deben ser validados por el administrador y respaldados por una fuente identificable. La plataforma debe distinguir entre dato oficial, dato aportado por administrador, dato validado en terreno y dato provisional.

## 4. Motor compartido de gestión

El motor común conecta los perfiles y administra:
- Identidades, organizaciones, territorios y membresías.
- Roles y permisos por territorio.
- Acuerdos comerciales entre administradores y operadores.
- Sectores, temporadas, disponibilidad, cupos y bloqueos.
- Solicitudes, reservas, órdenes de pago, pagos y devoluciones.
- Notificaciones y preferencias de contacto.
- Registro de aceptación de reglamentos y sus versiones.
- Control de ingreso, salida e incidencias.
- Auditoría de acciones y reportes.

### Flujo de descubrimiento y acceso directo

1. El pescador encuentra un cuerpo de agua en el mapa.
2. AnglerMap identifica si existe un territorio administrado y qué información puede publicar.
3. El pescador consulta sectores, reglas, tarifas y disponibilidad habilitada.
4. Selecciona fecha, sector y tamaño del grupo.
5. Registra los datos individuales requeridos y acepta las condiciones.
6. El motor valida cupos, cierres y reglas.
7. La solicitud sigue la modalidad de aprobación definida por el territorio.
8. Se emite la orden de pago cuando corresponda.
9. La confirmación de pago actualiza la reserva mediante una notificación verificable del proveedor.
10. Se entrega autorización e instrucciones de acceso.
11. Se registra ingreso y salida y se cierra la jornada.

### Flujo de operador con acuerdo vigente

1. El operador ingresa a su espacio de trabajo.
2. Selecciona un territorio y sector cubierto por su acuerdo.
3. Registra fecha, grupo y datos de los pescadores.
4. El motor valida cupos y condiciones contractuales.
5. La solicitud se procesa según las reglas del acuerdo y del territorio.
6. Se genera la reserva y el pago o liquidación que corresponda.
7. Ambas partes reciben confirmación y el historial queda registrado.

### Flujo de administración

1. El administrador configura el territorio, sectores, accesos y reglas.
2. Define cupos, tarifas, temporada y modalidad de confirmación.
3. Recibe solicitudes en una bandeja unificada.
4. El sistema resuelve automáticamente las que cumplen las reglas configuradas.
5. Las excepciones se elevan al responsable correspondiente.
6. El equipo administra operación, entradas, salidas e incidencias.
7. El administrador revisa ingresos, ocupación y desempeño.

## 5. Estados de solicitud, reserva y acceso

No deben confundirse la solicitud, el compromiso de pago, la reserva confirmada y la autorización de ingreso.

Estados funcionales recomendados:
- Solicitud recibida.
- Pendiente de aprobación.
- Rechazada.
- Aprobada, pendiente de pago.
- Orden de pago vencida.
- Pago confirmado.
- Reserva confirmada.
- Acceso habilitado.
- Ingreso registrado.
- Salida registrada.
- Finalizada.
- Cancelada o reembolsada, según corresponda.

La transición entre estados debe quedar auditada con actor, fecha, hora y motivo.

## 6. Política de aprobación y pagos

La modalidad se configura por territorio y, si se requiere, por sector o tipo de usuario.

### Modalidad A: aprobación manual
- El interesado envía una solicitud.
- El administrador o su equipo aprueba o rechaza.
- Al aprobar, se emite una orden de pago.
- El cupo se retiene durante un plazo configurable.
- El pago confirmado convierte la solicitud en reserva confirmada.
- Si vence la orden, se libera el cupo automáticamente.

### Modalidad B: confirmación automática
- El motor valida disponibilidad, reglas, límites y elegibilidad.
- Si se cumplen todas las condiciones, genera una orden de pago y retiene el cupo temporalmente.
- La confirmación verificable del pago confirma la reserva.
- Las excepciones se derivan al administrador.

La modalidad automática nunca debe omitir cierres, restricciones, cupos, reglas de conservación ni requisitos legales.

### Principios de pago
- El precio, moneda, impuestos aplicables y política de cancelación son configurables.
- El pago grupal debe identificar individualmente a cada pescador cuando la normativa o el territorio lo exijan.
- Una orden pendiente no equivale a pago ni a autorización de ingreso.
- Los pagos se confirman mediante webhooks firmados o mecanismos equivalentes del proveedor, con idempotencia y conciliación.
- No se almacenan datos de tarjetas en AnglerMap.
- Debe definirse contractualmente quién es el beneficiario del dinero, cómo se liquida y si AnglerMap cobra una comisión por plataforma.
- Si participa un operador, su comisión o tarifa debe quedar definida en el acuerdo comercial.
- Las devoluciones, anulaciones, contracargos y vencimientos deben tener trazabilidad.

## 7. Notificaciones y automatización

Canales potenciales:
- Correo transaccional.
- WhatsApp Business Platform mediante proveedor autorizado.
- Notificaciones dentro de la aplicación.
- Alertas operativas para el equipo administrador.

Eventos notificables:
- Nueva solicitud.
- Solicitud aprobada o rechazada.
- Orden de pago emitida y próxima a vencer.
- Pago confirmado o fallido.
- Reserva confirmada o cancelada.
- Cambio o cierre de sector.
- Instrucciones previas a la jornada.
- Registro de ingreso y salida.
- Incidencia o emergencia.

Las preferencias y datos de contacto se configuran por organización y usuario. Se debe registrar consentimiento, entrega y fallos. La interfaz de demostración no debe afirmar que envía mensajes reales.

## 8. Roles y permisos

Roles iniciales:
- Propietario o administrador principal del territorio.
- Encargado de reservas.
- Encargado de accesos y operación.
- Supervisor o auditor.
- Operador turístico titular y miembros de su equipo.
- Pescador recreativo.

Los permisos se asignan por organización, territorio y función. Aplicar mínimo privilegio: cada usuario solo accede a los datos y acciones necesarios para su trabajo. Las acciones sensibles —cambiar límites, tarifas, reglas, cerrar sectores, devolver pagos o conceder permisos— deben quedar auditadas.

## 9. Control operativo de acceso

La reserva debe poder vincularse a una autorización verificable:
- Código único o QR.
- Territorio, sector, fecha y ventana horaria si aplica.
- Titular y listado de integrantes.
- Estado del pago y autorización.
- Acceso y salida permitidos.
- Reglamento aceptado y versión vigente.

El administrador puede registrar entrada y salida desde su panel. En una etapa posterior se puede habilitar validación desde la app del usuario, con funcionamiento offline y sincronización posterior cuando la conectividad lo permita.

## 10. Indicadores para el administrador

- Solicitudes recibidas, aprobadas y rechazadas.
- Reservas confirmadas y cancelaciones.
- Ocupación por sector y jornada.
- Ingresos brutos, comisiones, devoluciones y liquidación neta.
- Ingreso por sector, temporada y canal.
- Operadores activos y rendimiento de acuerdos.
- Visitantes recurrentes.
- Días bloqueados y cierres.
- Incidencias y cumplimiento de registro de salida.

## 11. Modelo de datos conceptual

Entidades principales:
- User, Organization, Membership, Role, Permission.
- Territory, Waterbody, ParcelReference.
- ManagedArea, FishingSection, AccessPoint, EntryExitPoint, RestrictionZone.
- Season, AvailabilityRule, CapacityRule, Closure.
- OperatorAgreement, AgreementSection, CommercialCondition.
- AnglerProfile, FishingLicense, Group.
- AccessRequest, Reservation, ReservationParticipant.
- PaymentOrder, PaymentTransaction, Refund, Settlement.
- Regulation, RegulationVersion, AcceptanceRecord.
- CheckIn, CheckOut, Incident.
- NotificationPreference, NotificationEvent, AuditLog.

Las relaciones deben permitir que un usuario pertenezca a más de una organización, que un administrador gestione varios territorios y que un cuerpo de agua se relacione con múltiples unidades territoriales sin duplicar su identidad hidrográfica.

## 12. Seguridad, privacidad y gobernanza de datos

- Separación estricta de datos entre territorios y organizaciones.
- Control de acceso del lado servidor; ocultar botones no es autorización.
- Protección de datos personales y minimización de información.
- Consentimiento y finalidad para comunicaciones.
- Registro de cambios y operaciones sensibles.
- Validación de archivos y datos geográficos aportados.
- Copias de seguridad, recuperación y monitoreo.
- Procedencia, fecha y nivel de confianza para cada capa cartográfica.
- No publicar límites prediales privados, accesos o información sensible sin autorización y revisión.

## 13. Hoja de ruta de implementación

### Fase 1 — Base cartográfica
Consolidar hidrografía, referencias prediales, cuerpos de agua y procedencia de datos. Mantener explícita la diferencia entre cartografía de referencia y acceso autorizado.

### Fase 2 — Administrador de territorio
Crear territorio, validar cuerpo de agua, delimitar sectores, configurar accesos, temporadas, cupos, tarifas y reglamento. Incorporar equipo y permisos.

### Fase 3 — Motor de solicitudes y reservas
Disponibilidad, solicitudes, estados, aprobaciones, retención temporal de cupos, pagos, cancelaciones y auditoría.

### Fase 4 — Operadores turísticos
Acuerdos, sectores autorizados, grupos, solicitudes recurrentes y reportes comerciales.

### Fase 5 — Pescador recreativo
Descubrimiento en mapa, fichas de sectores, solicitud de acceso, pago, autorización y registro de jornada.

### Fase 6 — Automatización y expansión
Notificaciones reales, integraciones de pago, conciliación, QR, operación offline, analítica y despliegue multi-territorio.

## 14. Piloto Río del Medio

Río del Medio es el caso piloto para validar el modelo de administración y acceso, no una definición cartográfica definitiva.

Parámetros ilustrativos actuales:
- Seis sectores conceptuales.
- Máximo de cuatro pescadores por sector y jornada.
- Tarifa de referencia: CLP 30.000 por pescador y jornada.
- Capacidad teórica: 24 pescadores por jornada si los seis sectores están habilitados.
- Reglas propuestas: captura y liberación, no hacer fuego, permanecer dentro del sector, no dañar portones/cercos/alambres, usar accesos designados y registrar entrada y salida.

Los sectores, límites, accesos, cupos y reglas deben ser revisados y aprobados por el administrador antes de habilitar reservas reales. Los datos del prototipo son demostrativos y no representan disponibilidad ni permisos efectivos.

## 15. Criterios de aceptación del producto

- Un administrador no necesita conocimientos técnicos para configurar un territorio básico.
- Un operador puede solicitar sectores cubiertos por su acuerdo sin repetir el proceso de descubrimiento.
- Un pescador puede descubrir un sector administrado y comprender claramente sus condiciones antes de solicitar acceso.
- Los tres perfiles consultan la misma identidad geográfica y disponibilidad.
- No se permiten sobrecupos ni reservas sobre sectores cerrados.
- No se emite autorización de ingreso por una mera solicitud o por una orden impaga.
- Cada transición crítica queda registrada.
- El administrador puede delegar trabajo sin perder control.
- Los pagos, notificaciones y permisos reales solo se habilitan cuando las integraciones y controles correspondientes estén implementados.

---

**Decisión de arquitectura:** construir AnglerMap como una plataforma multi-tenant, geoespacial y transaccional, con tres experiencias de usuario y un motor compartido de administración, acuerdos, reservas, pagos y control de acceso.
