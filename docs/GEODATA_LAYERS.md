# AnglerMap · Capas geográficas modulares

## Principio de integración

La aplicación consume capas GeoJSON desde un catálogo único: `data/metadata/layers.json`.
El visor no depende de una fuente concreta. Una capa nueva se incorpora publicando su archivo y agregando una entrada al catálogo; no es necesario modificar el código del mapa.

## Estructura de datos

```
data/
  magallanes/                 # productos listos para consumo del visor
    communes.geojson
    waterbodies.geojson
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
