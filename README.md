# AnglerMap

Plataforma cartográfica de exploración para pesca recreativa en la Región de Magallanes, Chile.

## Demo pública

https://pristinewaters.github.io/anglermap/

## Prototipo web

La aplicación se ejecuta como sitio estático desde `index.html`. No requiere instalación ni cuenta de usuario.

### Funciones disponibles

- Mapa interactivo con cartografía satelital, topográfica y OpenStreetMap.
- Catálogo inicial de 14 ríos agrupados por territorio.
- Búsqueda de ríos y fichas informativas.
- Consulta de geometrías hidrográficas desde OpenStreetMap / Overpass, con caché local en el navegador.
- Meteorología de Open-Meteo vinculada al centro del mapa o al sector cartografiado.
- Capa de estaciones de monitoreo DGA en línea, cuando el servicio responde.
- Guardado local de aguas favoritas y puntos personales.
- Herramienta de medición de distancia.
- Catálogo modular para incorporar capas GeoJSON sin reescribir el visor.

## Alcance territorial inicial

Nueve comunas de Magallanes: Punta Arenas, Laguna Blanca, Río Verde, San Gregorio, Natales, Torres del Paine, Porvenir, Primavera y Timaukel. Cabo de Hornos y Antártica están fuera del alcance inicial.

## Estado y calidad de los datos

El prototipo web está operativo como visor y herramienta de exploración, pero **no debe interpretarse como cartografía oficial completa ni como guía de accesos autorizados**.

- Los trazados obtenidos desde OpenStreetMap son cartografía colaborativa y deben contrastarse con fuentes oficiales y conocimiento local.
- Una estación DGA cercana no necesariamente mide el río seleccionado; los datos dependen de la disponibilidad del servicio.
- Las capas estáticas de hidrografía consolidada y estaciones DGA GeoJSON permanecen pendientes de generación y validación. Los límites comunales usan MOP como fuente primaria y cuentan con respaldo institucional DPA 2020 de IDE MINVU (SUBDERE/IGM/DIFROL/INE), identificado como respaldo y sujeto a validación de vigencia.
- La extracción MOP/IGM/DGA se mantiene separada del visor. Los fallos temporales de servicios remotos no deben impedir abrir la aplicación.
- Guardados, puntos personales y preferencias se almacenan en el navegador local; todavía no existe sincronización entre dispositivos ni cuentas.
- Los perfiles de administrador, gestión de predios y permisos son demostrativos; no hay autenticación ni base de datos de usuarios.

## Fuentes y atribución

- OpenStreetMap contributors: https://www.openstreetmap.org/copyright
- Open-Meteo: https://open-meteo.com/
- Dirección General de Aguas (MOP): https://dga.mop.gob.cl/
- Instituto Geográfico Militar: https://www.igm.cl/
- Ministerio de Obras Públicas: https://www.mop.gob.cl/

## Desarrollo

- Aplicación: `index.html`
- Catálogo de capas: `data/metadata/layers.json`
- Generación de datos geográficos: `scripts/build_geodata.py`
- Workflow de actualización: `.github/workflows/update-geodata.yml`
- Especificación de capas: `docs/GEODATA_LAYERS.md`

Para activar una capa estática, publicar su GeoJSON en la ruta indicada por el catálogo y cambiar su estado a `available`. El visor valida el formato GeoJSON antes de agregarla al mapa.
