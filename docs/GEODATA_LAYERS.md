# AnglerMap · Capas geográficas

## Arquitectura: tres capas independientes

AnglerMap publica tres capas temáticas. Las dos primeras son cartográficas; la tercera representa puntos de monitoreo. Las estaciones DGA nunca se utilizan para crear, nombrar o corregir cuerpos de agua.

```
data/
  magallanes/
    roads.geojson          # MOP · caminos y accesos
    waterbodies.geojson    # DGA · ríos, esteros, lagos y lagunas
    dga_stations.geojson   # DGA · estaciones de la Red Hidrométrica Nacional
  metadata/
    layers.json
    sources.json
```

### 1. Caminos y accesos — MOP

- Servicio: [Red Vial Chile Base Gris, capa 3](https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Red_Vial_Chile_Base_gris/MapServer/3).
- Responsable: Dirección de Vialidad, Ministerio de Obras Públicas.
- Incluye caminos nacionales, regionales, provinciales, comunales y regionales de acceso según la descripción del servicio.
- La ficha describe datos disponibles a enero de 2021. La capa registra `NOMBRE_CAMINO`, `ROL`, `CLASIFICACION`, `CARPETA` y `RVO`, por lo que permite distinguir la jerarquía vial y la carpeta (pavimento, ripio, suelo natural y otras categorías). Incluye caminos nacionales, internacionales, regionales principales, provinciales, comunales, regionales de acceso y caminos en proceso de enrolamiento.
- La cobertura de 179 features de la primera descarga no se considera exhaustiva por sí sola. Se contrasta con los dimensionamientos oficiales MOP por longitud y carpeta de rodadura, además de la ficha regional IDE Magallanes. La cifra de registros no equivale al número total de rutas ni demuestra cobertura completa. El proceso calcula longitud geodésica aproximada total y por clasificación/carpeta, separando caminos regionales comunales y de acceso para compararlos con el benchmark estadístico MOP 2025 (1.678,203 km a diciembre de 2024). La comparación es de consistencia, no una igualdad exigible: las fechas y definiciones cartográficas pueden diferir.
- Es cartografía de referencia; no confirma transitabilidad actual, derecho de paso, servidumbre ni acceso a predios privados.
- Producto: `roads.geojson`, recortado y segmentado por comuna.

### 2. Cuerpos de agua — DGA (cartografía hidrográfica)

- Servicio: [IDE Recursos Hídricos y Glaciares](https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer).
- Subcapa 2: [Red de drenajes DGA](https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer/2), geometrías lineales y campos `NOMBRE` y `TIPO`.
- Subcapa 5: [Lagos DGA](https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer/5), geometrías poligonales con nombre, tipo, uso y área.
- Se incorporan todos los registros espaciales intersectantes de ambas subcapas; no se seleccionan solo destinos conocidos ni se filtran por popularidad.
- Los cursos lineales conservan el tipo DGA disponible (por ejemplo, río, estero, chorrillo, arroyo o canal); lagos y lagunas se clasifican a partir de los atributos DGA, usando el nombre solo como respaldo si el tipo está vacío.
- Solo se incorporan registros con un nombre informado por DGA; los registros sin nombre se excluyen del GeoJSON y del catálogo.
- Los registros se recortan e indexan por intersección geométrica con las nueve comunas. Si un mismo cuerpo cruza comunas, se generan segmentos comunales con el mismo `waterbody_id`.
- El catálogo agrupa por `waterbody_id`, no solo por nombre: dos cuerpos distintos con el mismo nombre no se fusionan accidentalmente.
- Limitaciones: la descripción de la red DGA indica que representa la mayoría, no necesariamente todas, las expresiones espaciales de drenaje. La capa de lagos tiene atribución DGA 2017 y puede omitir lagunas menores.

### 3. Estaciones de monitoreo — DGA (capa puntual independiente)

- Servicio: [Red Hidrométrica Nacional DGA, capa 0](https://rest-sit.mop.gob.cl/arcgis/rest/services/DGA/Red_Hidrometrica/MapServer/0).
- Representa puntos de estaciones fluviométricas, calidad de aguas, meteorológicas, control de niveles de lagos y embalses, sedimentometría, pozos, nivometría y glaciología.
- Se conserva como `dga_stations.geojson`, con ID de estación, nombre, tipo, vigencia, lugar, lago asociado cuando el atributo esté informado y atributos originales.
- La metadata cartográfica del servicio indica actualización julio de 2022. La vigencia individual se conserva como atributo y no se presume que toda estación esté operativa.
- La capa de puntos operacionales [DGA_MONITOREO_CAUCE](https://services3.arcgis.com/aSoEm9TBK2shtWjP/ArcGIS/rest/services/DGA_MONITOREO_CAUCE/FeatureServer/0) complementa los marcadores fluviométricos con caudal, nivel, precipitación, tendencia y alertas cuando hay datos disponibles. Son mediciones operacionales de estaciones, no atributos del río completo.
- Una estación es un punto de medición. Su nombre no define el nombre del río o lago. Una asociación con un cuerpo de agua solo se muestra cuando está expresamente respaldada por un atributo DGA; no se deduce por cercanía o coincidencia de nombres.

## Reglas de normalización y cobertura

- Alcance: Punta Arenas, Laguna Blanca, Río Verde, San Gregorio, Natales, Torres del Paine, Porvenir, Primavera y Timaukel.
- Los límites comunales MOP se usan únicamente como geometría auxiliar para recortar y asignar las tres capas; no se publican como capa temática.
- Cursos compartidos se representan en cada comuna atravesada, manteniendo el mismo ID de entidad entre segmentos.
- No se incorporan IGM, cuencas, subcuencas, subsubcuencas BNA ni hidrografía MOP.
- Los informes, decretos y catastros DGA se utilizan como contraste documental de nombres y contexto. No reemplazan la geometría de las capas cartográficas ni autorizan cambios toponímicos sin trazabilidad.
- La presencia de un cuerpo de agua, estación o camino no acredita acceso público ni permiso de pesca.

## Atributos principales

`waterbodies.geojson`:
- `waterbody_id`: identificador estable del registro DGA.
- `name`, `source_name`, `aliases`: nombre cartográfico y trazabilidad.
- `water_category`, `category_label`, `subtype`: categoría y tipo según DGA.
- `official_source`, `official_id`, `source_attributes`: fuente y atributos originales.
- `communes`: comuna del segmento.
- `representative_point`: referencia cartográfica, no acceso de pesca.

`dga_stations.geojson`:
- `station_id`, `station_name`, `station_type`, `vigencia`.
- `place`, `associated_lake` cuando DGA lo informa.
- `communes`, `official_source`, `source_attributes`.

`roads.geojson`:
- `road_id`, `name`, `route_code`, `classification`, `surface`, `status`.
- `communes`, `official_source`, `source_url`, `source_attributes`.

## Validación y publicación

El workflow descarga, valida y publica los tres GeoJSON y sus metadatos. Una capa solo pasa a estado `available` cuando el archivo existe, contiene geometrías válidas y supera la validación. Los archivos se preparan antes de reemplazar la versión publicada.

## Contraste de vialidad MOP

- [Red Vial Nacional · Dimensionamiento y Características 2025](https://vialidad.mop.gob.cl/uploads/sites/9/2025/08/Red-Vial-Nacional-Dimensionamiento-y-Caracteristicas-Ano-2025.pdf): estadísticas de longitud por carpeta y categoría; informa 1.678,203 km de caminos regionales comunales y de acceso en Magallanes a diciembre de 2024.
- [IDE Magallanes · Red Vial Región de Magallanes](https://idemagallanes.cl/magallanes/catalog/79/Red%20Vial%20Regi%C3%B3n%20de%20Magallanes): ficha regional de Dirección de Vialidad MOP, recurso vectorial SHP creado en noviembre de 2024 y marcado En Desarrollo; se utiliza como contraste documental, no como segunda capa de publicación.

## Fuentes DGA complementarias

- [Catastro Público de Aguas · Inventario Público de Lagos](https://dga.mop.gob.cl/servicios-de-informacion/catastro-publico-de-aguas/inventario-publico-de-cuencas-hidrograficas-y-lagos/).
- [Mapoteca Digital DGA](https://dga.mop.gob.cl/mapoteca-digital/).
- [Sistema Hidrométrico en Línea DGA](https://dga.mop.gob.cl/sistema-hidrometrico-en-linea/).
- [Estudios e informes técnicos DGA](https://dga.mop.gob.cl/servicios-de-informacion/catastro-publico-de-aguas/).

Los listados y documentos se pueden utilizar para contrastar nombres o detectar omisiones, sin convertir menciones textuales en geometrías inventadas.
