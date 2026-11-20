# AnglerMap · Capas geográficas modulares

## Principio de integración

La aplicación consume capas GeoJSON desde un catálogo único: `data/metadata/layers.json`.
El visor no depende de una fuente concreta. Una capa nueva se incorpora publicando su archivo y agregando una entrada al catálogo; no es necesario modificar el código del mapa.

## Estructura de datos

```
data/
  magallanes/                 # productos listos para consumo del visor
    communes.geojson
    provinces.geojson
    waterbodies.geojson
    dga_hydro_units.geojson
    dga_stations.geojson
  sources/                    # archivos organizados por fuente
    mop/
      boundaries/
      hydrography/
    igm/
      hydrography/
    dga/
      stations/
  metadata/
    layers.json               # catálogo que consume la aplicación
    sources.json              # procedencia y trazabilidad de datos
```

Los directorios de fuentes son repositorios de origen/procesamiento. Los GeoJSON publicados en `data/magallanes/` son productos normalizados para la aplicación. Se pueden mantener ambos cuando sea necesario conservar el original y el producto depurado.

## Productos hidrográficos

- `waterbodies.geojson`: geometrías lineales y poligonales de ríos/esteros, lagos, lagunas y embalses. Conserva nombre original, alias, tipo, atributos de origen, fuente, identificadores, comunas y provincias.
- `dga_hydro_units.geojson`: unidades BNA DGA separadas por nivel (cuenca, subcuenca y subsubcuenca), con códigos y nombres oficiales.
- `dga_stations.geojson`: estaciones de monitoreo DGA. Son puntos de observación y no sustituyen la geometría de un curso de agua.
- `communes.geojson` y `provinces.geojson`: límites administrativos usados para recortar y clasificar las geometrías.

La asociación de cada agua con unidades hidrográficas se calcula por intersección espacial entre geometrías. No se infiere un río a partir del nombre de una estación ni se asigna una comuna por la cuenca completa. Los cursos compartidos pueden figurar en más de una comuna cuando la geometría intersecta sus límites.

La capa DGA de red de drenaje y las unidades BNA se publican en la IDE de la SMA con atribución explícita a DGA/Banco Nacional de Aguas. La procedencia y fecha de extracción se conservan en `sources.json` y en los atributos de cada entidad.

La capa MOP `sistema_lacustre` (ID 17) es mixta: además de lagos y lagunas contiene polígonos de ríos, esteros, embalses, salares, campos de hielo, glaciares y ventisqueros. El catálogo retiene Río, Estero, Embalse, Lago y Laguna como categorías diferenciadas; no clasifica salares ni elementos glaciares como lagos.

La capa DGA `Cuencas` (ID 10) informa actualización hasta 2004 y datum desconocido, asumido WGS84 por su publicador. Se utiliza como referencia hidrográfica y no como deslinde parcelario de alta precisión. La red de drenaje DGA (ID 2) indica que representa la mayoría, no necesariamente la totalidad, de las expresiones espaciales de drenaje.

## Diccionario de atributos

### `waterbodies.geojson`

- `waterbody_id`: identificador estable por registro y fuente.
- `name`: nombre normalizado que usa el catálogo; `source_name` conserva el rótulo original.
- `aliases` y `toponymy_status`: nombres alternativos y estado de conciliación toponímica.
- `water_type` / `water_category`: tipo de geometría y categoría de interfaz (`river`, `lake`, `lagoon`, `reservoir`).
- `official_source`, `official_id`, `source_attributes`: trazabilidad y atributos originales.
- `communes`, `provinces`: unidades administrativas intersectadas por la geometría.
- `hydro_units`, `basins`, `subbasins`, `subsubbasins`: unidades BNA intersectadas y sus nombres/códigos.
- `representative_point`: punto de referencia cartográfico; no es acceso de pesca.
- `source_confidence`: distingue geometría de fuente oficial de correcciones toponímicas locales.

### `dga_hydro_units.geojson`

- `unit_level`: `basin`, `subbasin` o `subsubbasin`.
- `name`, `code`, `basin_code`, `subbasin_code`, `subsubbasin_code`: nomenclatura y códigos BNA.
- `communes`, `provinces`: comunas y provincias intersectadas.
- `source_url`, `source_attributes`: servicio de origen y atributos originales.

### `dga_stations.geojson`

Conserva el identificador y los atributos de la estación DGA. La estación no se transforma en un río ni se asigna a un curso solo por proximidad.

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
