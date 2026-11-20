# AnglerMap

Plataforma cartográfica de exploración para pesca recreativa en la Región de Magallanes, Chile.

## Demo pública

https://pristinewaters.github.io/anglermap/

## Funciones disponibles

- Mapa interactivo con cartografía satelital, topográfica y OpenStreetMap.
- Catálogo DGA de cuerpos de agua con nombre (ríos, esteros, lagos y lagunas) disponibles en las capas seleccionadas, agrupado por las nueve comunas.
- Cuerpos que atraviesan más de una comuna conservan una identidad común y se muestran en cada comuna correspondiente.
- Búsqueda de aguas y fichas con procedencia y comuna.
- Selección de un cuerpo de agua con zoom a la geometría cartográfica DGA disponible.
- Capa MOP de caminos y accesos, activable sobre el mapa.
- Capa independiente de estaciones DGA, con inventario de tipos de estación y mediciones operacionales fluviométricas cuando están disponibles.
- Meteorología Open-Meteo, favoritos, puntos personales y herramienta de medición.

## Alcance territorial

Nueve comunas: Punta Arenas, Laguna Blanca, Río Verde, San Gregorio, Natales, Torres del Paine, Porvenir, Primavera y Timaukel. Cabo de Hornos y Antártica quedan fuera del alcance inicial.

## Arquitectura de datos

1. **Caminos y accesos — MOP:** Red Vial Chile Base Gris, capa 3.
2. **Cuerpos de agua — DGA:** Red de drenajes, subcapa 2, e inventario de lagos, subcapa 5, consolidados en `waterbodies.geojson`.
3. **Estaciones — DGA:** Red Hidrométrica Nacional, capa 0, en `dga_stations.geojson`; los datos operacionales fluviométricos complementan sus marcadores.

Las estaciones son puntos de monitoreo y no definen el nombre ni la geometría del cuerpo de agua. Los nombres de cuerpos de agua provienen de la cartografía DGA, no de nombres de estaciones.

## Estado y limitaciones

El prototipo es una herramienta de exploración; no debe interpretarse como cartografía oficial completa ni como guía de accesos autorizados.

- La DGA describe su red de drenajes como representación de la mayoría, no necesariamente todas, las expresiones espaciales de drenaje.
- La capa de lagos DGA tiene atribución 2017 y puede no incluir lagunas menores. Los informes y el Inventario Público de Lagos se usan para contraste documental y detección de omisiones; no se inventan geometrías a partir de menciones textuales.
- La Red Hidrométrica Nacional consultada indica actualización cartográfica julio 2022; la vigencia de cada estación debe revisarse individualmente.
- La capa de caminos MOP describe datos disponibles a enero de 2021; no confirma transitabilidad actual, derecho de paso ni acceso privado.
- La presencia de un cuerpo de agua, estación o camino no acredita acceso público ni permiso de pesca.
- Las geometrías OSM/Overpass son complementarias y no reemplazan las geometrías DGA.
- Los archivos solo se consideran disponibles cuando el workflow los descarga, valida y activa en el catálogo.

## Fuentes

- MOP · Red Vial Chile Base Gris: https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Red_Vial_Chile_Base_gris/MapServer/3
- DGA · Red de drenajes: https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer/2
- DGA · Lagos: https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer/5
- DGA · Red Hidrométrica Nacional: https://rest-sit.mop.gob.cl/arcgis/rest/services/DGA/Red_Hidrometrica/MapServer/0
- DGA · Datos operacionales de cauces: https://services3.arcgis.com/aSoEm9TBK2shtWjP/ArcGIS/rest/services/DGA_MONITOREO_CAUCE/FeatureServer/0
- DGA · Catastro Público de Aguas: https://dga.mop.gob.cl/servicios-de-informacion/catastro-publico-de-aguas/
- OpenStreetMap contributors: https://www.openstreetmap.org/copyright
- Open-Meteo: https://open-meteo.com/

## Desarrollo

- Aplicación: `index.html`
- Catálogo: `data/metadata/layers.json`
- Generación: `scripts/build_geodata.py`
- Workflow: `.github/workflows/update-geodata.yml`
- Productos: `roads.geojson`, `waterbodies.geojson`, `dga_stations.geojson`.
- Especificación: `docs/GEODATA_LAYERS.md`
