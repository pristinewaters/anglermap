# AnglerMap · Capas geográficas modulares

## Principio de integración

La aplicación consume capas GeoJSON desde un catálogo único: `data/metadata/layers.json`.
El visor no depende de una fuente concreta. Una capa nueva se incorpora publicando su archivo y agregando una entrada al catálogo; no es necesario modificar el código del mapa.

## Arquitectura de las dos capas temáticas

AnglerMap utiliza dos fuentes institucionales separadas y dos productos GeoJSON normalizados:

```
data/
  magallanes/
    roads.geojson          # MOP · caminos y accesos
    waterbodies.geojson    # DGA · ríos, esteros, lagos y lagunas
  metadata/
    layers.json
    sources.json
```

### 1. Caminos y accesos — MOP

- Servicio: [Red Vial Chile Base Gris, capa 3](https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Red_Vial_Chile_Base_gris/MapServer/3).
- Responsable: Dirección de Vialidad, Ministerio de Obras Públicas.
- Incluye caminos nacionales, regionales, comunales y caminos regionales de acceso según la descripción de la capa.
- El servicio describe datos disponibles a enero de 2021. Se debe mostrar como cartografía vial oficial, no como confirmación de transitabilidad, permiso de paso, servidumbre o acceso a predios privados.
- Producto: `roads.geojson`, recortado y segmentado por las nueve comunas.

### 2. Cuerpos de agua — DGA

- Servicio: [IDE Recursos Hídricos y Glaciares](https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer).
- Red de drenajes DGA, subcapa 2: geometrías lineales de ríos, esteros y expresiones de drenaje.
- Lagos DGA, subcapa 5: geometrías poligonales con nombre, tipo, uso y área. Cuando el atributo `TIPO` identifica una laguna, se conserva la categoría Laguna.
- Las dos subcapas se consolidan en un único producto `waterbodies.geojson`, con categorías de interfaz río/estero, lago y laguna.
- Se preservan nombre de origen, alias cuando existan, atributos originales, ID de fuente, comuna y procedencia.
- La red de drenajes DGA representa la mayoría, no necesariamente la totalidad, de las expresiones espaciales de drenaje. El inventario de lagos DGA publicado informa datos de 2017; puede no contener todas las lagunas menores.

### Reglas de normalización

- La geometría se intersecta con los límites comunales MOP para recortar los trazados y organizar el catálogo territorial. Los límites son auxiliares de recorte, no una tercera capa temática.
- Un curso que atraviesa varias comunas se divide en segmentos comunales; la interfaz agrupa los segmentos del mismo nombre y categoría.
- No se agregan nombres manualmente ni se infieren ríos desde estaciones de monitoreo.
- No se descargan ni publican capas IGM, estaciones DGA, cuencas, subcuencas o subsubcuencas en este alcance.
- La corrección toponímica Río Serrano/Río del Oro en Primavera se conserva como antecedente para revisión de nombres; no se utiliza como una regla general para reasignar cuerpos de agua.
- Una geometría no acredita acceso público ni autorización de pesca.

### Diccionario mínimo de atributos

`waterbodies.geojson`:
- `waterbody_id`: identificador estable del registro.
- `name`: nombre que muestra el catálogo.
- `source_name`: nombre original de la fuente.
- `aliases`, `toponymy_status`, `toponymy_note`: trazabilidad toponímica cuando aplique.
- `water_category`: `river`, `lake` o `lagoon`.
- `official_source`, `official_id`, `source_attributes`: procedencia e identificación.
- `communes`: comuna(s) intersectada(s).
- `representative_point`: referencia cartográfica, no acceso de pesca.

`roads.geojson`:
- `road_id`, `name`, `route_code`: identificación del tramo.
- `classification`, `surface`, `status`: atributos viales informados por MOP.
- `communes`: comuna del segmento.
- `official_source`, `source_url`, `source_attributes`: procedencia y trazabilidad.

## Incorporar una capa

1. Guardar el GeoJSON normalizado en `data/magallanes/` o en la ruta de producto definida para esa capa.
2. Agregar una entrada a `data/metadata/layers.json` con `id`, `name`, `file`, `source`, `status`, `visible_by_default` y `style`.
3. Cambiar `status` a `available` solo después de validar el archivo como GeoJSON FeatureCollection, su CRS (WGS84 / EPSG:4326), geometrías, cobertura y procedencia.
4. Publicar los cambios. El visor detecta la capa en el panel **Capas cartográficas** y la carga al activarla.

Las entradas con estado `pending` o `planned` aparecen como futuras y no generan solicitudes de red. Así, MOP puede incorporarse más adelante sin recalcular IGM/DGA ni reescribir el visor.

## Estados

- `planned`: fuente/capa prevista, aún no integrada.
- `pending`: producto definido, archivo todavía no validado/publicado.
- `available`: GeoJSON validado y disponible para el visor.

## Reglas de calidad

- No marcar una capa como `available` si el archivo no existe o está incompleto.
- Mantener procedencia, fecha de descarga, licencia y sistema de referencia en `sources.json`.
- Una falla de una fuente no debe bloquear la actualización de otra.
- Los procesos de generación deben escribir archivos temporales y publicar solo después de validar.
