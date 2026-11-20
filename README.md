# AnglerMap

Plataforma cartográfica de exploración para pesca recreativa en la Región de Magallanes, Chile.

## Demo pública

https://pristinewaters.github.io/anglermap/

## Prototipo web

La aplicación se ejecuta como sitio estático desde `index.html`. No requiere instalación ni cuenta de usuario.

### Funciones disponibles

- Mapa interactivo con cartografía satelital, topográfica y OpenStreetMap.
- Catálogo DGA de ríos/esteros, lagos y lagunas, agrupado por las nueve comunas.
- Búsqueda de aguas y fichas informativas con procedencia y comuna.
- Selección de un cuerpo de agua con enfoque automático de su geometría cartográfica disponible.
- OpenStreetMap / Overpass como fuente complementaria cuando falta geometría estática validada.
- Meteorología de Open-Meteo vinculada al centro del mapa o al sector cartografiado.
- Capa de caminos y accesos MOP, activable sobre el mapa.
- Guardado local de aguas favoritas y puntos personales.
- Herramienta de medición de distancia.
- Catálogo modular para incorporar capas GeoJSON sin reescribir el visor.

## Alcance territorial inicial

Nueve comunas de Magallanes: Punta Arenas, Laguna Blanca, Río Verde, San Gregorio, Natales, Torres del Paine, Porvenir, Primavera y Timaukel. Cabo de Hornos y Antártica están fuera del alcance inicial.

## Estado y calidad de los datos

El prototipo web está operativo como visor y herramienta de exploración, pero **no debe interpretarse como cartografía oficial completa ni como guía de accesos autorizados**.

- Los trazados obtenidos desde OpenStreetMap son cartografía colaborativa y deben contrastarse con fuentes oficiales y conocimiento local.
- La capa de caminos usa la Red Vial Chile Base Gris del MOP; la ficha del servicio informa datos disponibles a enero de 2021. No confirma transitabilidad actual, derecho de paso ni accesos privados.
- El catálogo de aguas utiliza exclusivamente la red de drenajes y el inventario de lagos DGA, consolidados en un GeoJSON y agrupados espacialmente por comuna.
- Cuencas, subcuencas, unidades BNA e hidrografía IGM quedan fuera del alcance de las dos capas principales.
- Los rótulos discrepantes se conservan con trazabilidad. La referencia Río Serrano/Río del Oro en Primavera queda como antecedente toponímico, sin introducir reglas adicionales de clasificación.
- Las capas deben considerarse disponibles solo después de que el workflow las descargue, valide y active en el catálogo. La existencia del código de extracción no acredita que los archivos se hayan generado correctamente.
- La extracción MOP/IGM/DGA se mantiene separada del visor. Los fallos temporales de servicios remotos no deben impedir abrir la aplicación.
- Guardados, puntos personales y preferencias se almacenan en el navegador local; todavía no existe sincronización entre dispositivos ni cuentas.
- Los perfiles de administrador, gestión de predios y permisos son demostrativos; no hay autenticación ni base de datos de usuarios.

## Fuentes y atribución

- MOP · Red Vial Chile Base Gris: https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Red_Vial_Chile_Base_gris/MapServer/3
- OpenStreetMap contributors: https://www.openstreetmap.org/copyright
- Open-Meteo: https://open-meteo.com/
- Dirección General de Aguas (MOP): https://dga.mop.gob.cl/
- IDE de la Superintendencia del Medio Ambiente, capas hidrográficas con atribución a DGA/Banco Nacional de Aguas: https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer
- Ministerio de Obras Públicas: https://www.mop.gob.cl/

## Desarrollo

- Aplicación: `index.html`
- Catálogo de capas: `data/metadata/layers.json`
- Generación de datos geográficos: `scripts/build_geodata.py`
- Workflow de actualización: `.github/workflows/update-geodata.yml`
- Productos geográficos: `roads.geojson` (MOP) y `waterbodies.geojson` (DGA).
- Especificación de capas: `docs/GEODATA_LAYERS.md`

Para activar una capa estática, publicar su GeoJSON en la ruta indicada por el catálogo y cambiar su estado a `available`. El visor valida el formato GeoJSON antes de agregarla al mapa.
