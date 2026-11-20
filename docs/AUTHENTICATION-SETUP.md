# AnglerMap · Cuentas y autenticación

## Implementado en esta rama

- Registro con correo y contraseña, inicio/cierre de sesión y recuperación por correo mediante Supabase Auth.
- Sesión persistente gestionada por Supabase; no se almacenan contraseñas ni tokens manualmente en localStorage.
- Sincronización de preferencias del perfil en `public.profiles`.
- Migración SQL inicial con perfiles, roles múltiples por usuario, territorios, membresías, sectores, acuerdos con operadores, reservas y eventos de acceso.
- Row Level Security (RLS) activada en todas las tablas creadas.
- El perfil recreativo se asigna automáticamente al crear la cuenta. El rol de administrador territorial se concede al crear un territorio y no puede autoasignarse desde el navegador.

## Activación necesaria (una sola vez)

El repositorio no tenía backend ni proyecto de base de datos conectado. Por seguridad, no se puede activar una cuenta real hasta crear/configurar el proyecto Supabase. El código queda preparado, pero el login se mantiene deshabilitado mientras falte configuración.

1. Crear un proyecto Supabase para AnglerMap.
2. En SQL Editor, ejecutar íntegramente `supabase/migrations/202611200001_anglermap_core.sql`.
3. Copiar Project URL y anon/publishable key desde Project Settings → API.
4. Pegarlas en `scripts/supabase-config.js` (ambos valores son claves públicas; nunca usar `service_role`).
5. En Authentication → URL Configuration, establecer el dominio de producción y agregar los dominios Preview/local que se usarán como Redirect URLs.
6. En Authentication → Providers, habilitar Email. Mantener confirmación de correo activada para producción y configurar SMTP transaccional propio antes de abrir el registro al público.
7. Publicar de nuevo la rama en Vercel/Pages y probar alta, confirmación de correo, inicio, cierre y recuperación.

## Seguridad y límites de esta primera entrega

- RLS protege perfiles y datos por usuario/territorio; no se concede el rol privilegiado por un selector de interfaz.
- La creación de reservas desde navegador solo permite insertar solicitudes en estado `requested`. No hay endpoint para aprobar, confirmar pagos ni alterar estados.
- No se implementan todavía retención de cupos, cálculo transaccional de capacidad, webhooks de pago, correo operativo, WhatsApp ni check-in/check-out autorizado. Esos procesos requieren funciones backend confiables.
- Las preferencias antiguas en localStorage se conservan. Al iniciar sesión se sincronizan en la tabla de perfil.
- La configuración Supabase se deja vacía deliberadamente. No inventar credenciales ni poner claves secretas en GitHub.

## Modelo de roles

Una misma cuenta puede tener varios roles. El usuario no necesita crear cuentas distintas para ser pescador, guía/operador y administrador territorial. La pertenencia y los permisos efectivos se resuelven por territorio, no por el selector visual del prototipo.

## Siguiente implementación técnica

1. Provisionar Supabase y configurar los dominios/SMTP.
2. Ejecutar pruebas de integración de autenticación.
3. Añadir funciones server-side para aprobación, cupos, reservas y pagos.
4. Incorporar invitaciones y gestión de equipo del administrador territorial.
