
import hashlib
import json
import re
from numbers import Integral
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import requests
from shapely.geometry import (
    shape,
    mapping,
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    GeometryCollection,
    Point,
    LinearRing,
    box
)
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "magallanes"
META = ROOT / "data" / "metadata"

BASE = "https://rest-sit.mop.gob.cl/arcgis/rest/services"

URL_COMMUNES = BASE + "/MAPA_BASE/LIMITES/MapServer/2"
# Respaldo institucional DPA 2020 publicado por MINVU con datos coordinados por SUBDERE, IGM, DIFROL e INE.
# Se utiliza solo si el servicio MOP no responde; no reemplaza la fuente MOP como referencia primaria.
URL_COMMUNES_FALLBACK = "https://geoide.minvu.cl/server/rest/services/Hosted/DS19/FeatureServer/3"
URL_PROVINCES = BASE + "/MAPA_BASE/LIMITES/MapServer/1"

URL_IGM = BASE + "/MAPA_BASE/IGM50/MapServer"
URL_IGM_RIVERS = URL_IGM + "/15"
URL_IGM_WATERS = URL_IGM + "/18"

URL_MOP_HYDRO = BASE + "/MAPA_BASE/RED_HIDROGRAFICA/MapServer"
URL_MOP_RIVERS = URL_MOP_HYDRO + "/16"
URL_MOP_LAKES = URL_MOP_HYDRO + "/17"

URL_DGA_STATIONS = (
    BASE + "/DGA/Red_Hidrometrica/MapServer/0"
)

# Capas DGA/Banco Nacional de Aguas publicadas en la IDE de la SMA.
URL_DGA_IDE = "https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer"
URL_DGA_DRAINAGE = URL_DGA_IDE + "/2"
URL_DGA_LAKES = URL_DGA_IDE + "/5"
URL_DGA_BASINS = URL_DGA_IDE + "/10"
URL_DGA_SUBBASINS = URL_DGA_IDE + "/9"
URL_DGA_SUBSUBBASINS = URL_DGA_IDE + "/8"


# Cabo de Hornos y Antártica quedan fuera del alcance.
TARGET_COMMUNES = {
    "punta arenas": "Punta Arenas",
    "laguna blanca": "Laguna Blanca",
    "rio verde": "Río Verde",
    "san gregorio": "San Gregorio",
    "natales": "Natales",
    "torres del paine": "Torres del Paine",
    "porvenir": "Porvenir",
    "primavera": "Primavera",
    "timaukel": "Timaukel"
}

EXPECTED_COMMUNES = 9

BATCH_SIZE = 100
MAX_RETRIES = 4

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AnglerMap-Geodata/3.3"
})

COMMUNE_GEOMETRIES = []
COMMUNE_TREE = None
COMMUNE_TREE_LOOKUP = {}
PROVINCE_GEOMETRIES = []


def log(message):
    print("[AnglerMap] " + str(message), flush=True)


def normalize(value):
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFD", value)

    value = "".join(
        c for c in value
        if unicodedata.category(c) != "Mn"
    )

    return re.sub(r"\s+", " ", value)


def request_json(url, params=None, method="GET"):
    params = dict(params or {})
    params.setdefault("f", "json")

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            if method.upper() == "POST":
                response = SESSION.post(
                    url,
                    data=params,
                    timeout=(20, 120)
                )
            else:
                response = SESSION.get(
                    url,
                    params=params,
                    timeout=(20, 120)
                )

            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    "HTTP " + str(response.status_code)
                )

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as parse_error:
                body_preview = response.text[:500].replace("\n", " ")
                raise RuntimeError(
                    "Respuesta no JSON del servicio ArcGIS "
                    + "(HTTP " + str(response.status_code)
                    + ", Content-Type="
                    + str(response.headers.get("Content-Type"))
                    + "): " + body_preview
                ) from parse_error

            if "error" in data:
                raise RuntimeError(
                    json.dumps(
                        data["error"],
                        ensure_ascii=False
                    )
                )

            return data

        except Exception as error:
            last_error = error

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt

                log(
                    "Consulta fallida. Reintento "
                    + str(attempt + 1)
                    + " en "
                    + str(wait)
                    + " segundos: "
                    + str(error)
                )

                time.sleep(wait)

    raise RuntimeError(
        "Falló la consulta: "
        + url
        + " · "
        + str(last_error)
    )


def layer_metadata(layer_url):
    data = request_json(layer_url)
    fields = data.get("fields", [])

    if not fields:
        raise RuntimeError(
            "La capa no informa campos consultables: "
            + layer_url
        )

    oid = data.get("objectIdField")

    if not oid:
        for field in fields:
            if field.get("type") == "esriFieldTypeOID":
                oid = field.get("name")
                break

    if not oid:
        raise RuntimeError(
            "No se identificó OBJECTID en "
            + layer_url
        )

    return data, oid, [
        field.get("name")
        for field in fields
        if field.get("name")
    ]


def find_field(fields, candidates):
    lookup = {
        normalize(field): field
        for field in fields
    }

    for candidate in candidates:
        found = lookup.get(normalize(candidate))

        if found:
            return found

    return None


def esri_to_shape(geometry):
    if not geometry:
        return None

    if "paths" in geometry:
        paths = geometry["paths"]

        if not paths:
            return None

        if len(paths) == 1:
            result = LineString(paths[0])
        else:
            result = MultiLineString(paths)

    elif "rings" in geometry:
        rings = geometry["rings"]

        if not rings:
            return None

        outer_rings = []
        inner_rings = []

        for coordinates in rings:
            ring = LinearRing(coordinates)

            polygon = Polygon(coordinates)

            if polygon.is_empty or polygon.area == 0:
                continue

            # ArcGIS normalmente utiliza anillos exteriores
            # en sentido horario e interiores en sentido antihorario.
            if ring.is_ccw:
                inner_rings.append(polygon)
            else:
                outer_rings.append(polygon)

        polygons = []

        for outer in outer_rings:
            holes = []

            for inner in inner_rings:
                if outer.contains(inner.representative_point()):
                    holes.append(list(inner.exterior.coords))

            polygon = Polygon(
                outer.exterior.coords,
                holes
            )

            if not polygon.is_valid:
                polygon = polygon.buffer(0)

            if not polygon.is_empty:
                polygons.append(polygon)

        if not polygons:
            return None

        if len(polygons) == 1:
            result = polygons[0]
        else:
            result = MultiPolygon(polygons)

    elif "x" in geometry and "y" in geometry:
        result = Point(
            geometry["x"],
            geometry["y"]
        )

    else:
        return None

    if result.is_empty:
        return None

    if not result.is_valid:
        result = result.buffer(0)

    return result


def arcgis_polygon_geometry(geometry):
    """
    Convierte Polygon/MultiPolygon Shapely a geometría ArcGIS.
    Los anillos se orientan según la convención de ArcGIS:
    exteriores horarios e interiores antihorarios.
    """
    if geometry.is_empty:
        return None

    if geometry.geom_type == "Polygon":
        polygons = [geometry]
    elif geometry.geom_type == "MultiPolygon":
        polygons = list(geometry.geoms)
    else:
        raise RuntimeError(
            "La consulta espacial requiere Polygon/MultiPolygon; recibido: "
            + geometry.geom_type
        )

    rings = []
    for polygon in polygons:
        polygon = orient(polygon, sign=-1.0)
        rings.append([list(point) for point in polygon.exterior.coords])
        for interior in polygon.interiors:
            rings.append([list(point) for point in interior.coords])

    return {
        "rings": rings,
        "spatialReference": {"wkid": 4326}
    }


def fetch_ids_single(layer_url, where="1=1", geometry=None):
    """Consulta ArcGIS para un único rectángulo espacial."""
    params = {
        "where": where,
        "returnIdsOnly": "true"
    }

    if geometry is not None:
        if geometry.is_empty:
            return []

        xmin, ymin, xmax, ymax = geometry.bounds
        envelope = {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "spatialReference": {"wkid": 4326}
        }
        params.update({
            "geometry": json.dumps(envelope, separators=(",", ":")),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects"
        })

    data = request_json(
        layer_url + "/query",
        params,
        method="GET"
    )
    return data.get("objectIds") or []


def fetch_ids(layer_url, where="1=1", geometry=None):
    """
    Consulta por teselas espaciales pequeñas. Los servicios ArcGIS del MOP
    fallan o agotan tiempo con envolventes extensas de comunas australes.
    Cada tesela reduce el coste de la consulta remota; los IDs se deduplican
    y la geometría se filtra exactamente después de descargar los features.
    """
    if geometry is None or geometry.is_empty:
        return fetch_ids_single(layer_url, where, geometry)

    xmin, ymin, xmax, ymax = geometry.bounds
    tile_size = 0.5  # grados; aproximadamente 55 km en latitudes australes
    x = xmin
    tile_count = 0
    ids = set()

    while x < xmax:
        y = ymin
        x2 = min(x + tile_size, xmax)
        while y < ymax:
            y2 = min(y + tile_size, ymax)
            tile = box(x, y, x2, y2)

            if geometry.intersects(tile):
                tile_count += 1
                tile_ids = fetch_ids_single(layer_url, where, tile)
                ids.update(tile_ids)

                if tile_count % 10 == 0:
                    log(
                        "Teselas consultadas: " + str(tile_count)
                        + " · IDs únicos: " + str(len(ids))
                    )

            y = y2
        x = x2

    log(
        "Consulta espacial por teselas completada: "
        + str(tile_count) + " teselas · "
        + str(len(ids)) + " IDs únicos"
    )
    return sorted(ids)


def fetch_batch(layer_url, ids, oid_field):
    if not ids:
        return []

    data = request_json(
        layer_url + "/query",
        {
            "objectIds": ",".join(map(str, ids)),
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326"
        },
        method="POST"
    )

    if data.get("exceededTransferLimit"):
        raise RuntimeError(
            "ArcGIS excedió el límite de transferencia."
        )

    features = data.get("features", [])

    received = {
        str(
            feature.get("attributes", {}).get(oid_field)
        )
        for feature in features
    }

    missing = set(map(str, ids)) - received

    if missing:
        raise RuntimeError(
            "Faltan registros en la descarga: "
            + ", ".join(sorted(missing))
        )

    return features


def fetch_features(layer_url, where="1=1", geometry=None):
    metadata, oid_field, fields = layer_metadata(layer_url)

    # Consultar por comuna evita que el bounding box conjunto
    # abarque grandes superficies ajenas al territorio objetivo.
    if geometry is not None and COMMUNE_GEOMETRIES:
        candidate_ids = set()

        for commune in COMMUNE_GEOMETRIES:
            commune_ids = fetch_ids(
                layer_url,
                where,
                commune["geometry"]
            )
            candidate_ids.update(commune_ids)
            log(
                "Candidatos "
                + commune["name"]
                + ": "
                + str(len(commune_ids))
            )

        ids = sorted(candidate_ids)
    else:
        ids = sorted(set(fetch_ids(layer_url, where, geometry)))

    log(
        layer_url
        + " · registros candidatos: "
        + str(len(ids))
    )

    output = []

    for start in range(0, len(ids), BATCH_SIZE):
        batch = ids[start:start + BATCH_SIZE]

        output.extend(
            fetch_batch(
                layer_url,
                batch,
                oid_field
            )
        )

        if (start // BATCH_SIZE) % 10 == 0 or start + len(batch) == len(ids):
            log(
                "Descargados "
                + str(len(output))
                + " / "
                + str(len(ids))
            )

        time.sleep(0.05)

    if len(output) != len(ids):
        raise RuntimeError(
            "Descarga incompleta: "
            + layer_url
        )

    return output, fields, metadata


def records_from_features(features, label="geometrías"):
    output = []
    total = len(features)

    log("Procesando " + str(total) + " " + label)

    for index, feature in enumerate(features, start=1):
        geometry = esri_to_shape(
            feature.get("geometry")
        )

        if geometry is not None and not geometry.is_empty:
            output.append({
                "geometry": geometry,
                "properties": feature.get("attributes") or {}
            })

        if index % 5000 == 0 or index == total:
            log(
                "Procesamiento "
                + label
                + ": "
                + str(index)
                + " / "
                + str(total)
            )

    return output


def build_commune_spatial_index():
    global COMMUNE_TREE, COMMUNE_TREE_LOOKUP

    geometries = [item["geometry"] for item in COMMUNE_GEOMETRIES]
    COMMUNE_TREE = STRtree(geometries)
    COMMUNE_TREE_LOOKUP = {
        id(geometry): index
        for index, geometry in enumerate(geometries)
    }


def intersecting_provinces(geometry):
    return [
        item["name"]
        for item in PROVINCE_GEOMETRIES
        if geometry.intersects(item["geometry"])
    ]


def intersecting_communes(geometry):
    if COMMUNE_TREE is None:
        return [
            item for item in COMMUNE_GEOMETRIES
            if geometry.intersects(item["geometry"])
        ]

    matches = []
    for candidate in COMMUNE_TREE.query(geometry):
        # Shapely 2 returns integer indices; Shapely 1 returns geometries.
        if isinstance(candidate, Integral):
            index = candidate
        else:
            index = COMMUNE_TREE_LOOKUP.get(id(candidate))
            if index is None:
                continue

        commune = COMMUNE_GEOMETRIES[index]
        if geometry.intersects(commune["geometry"]):
            matches.append(commune)

    return matches


def geojson_feature(geometry, properties):
    return {
        "type": "Feature",
        "geometry": mapping(geometry),
        "properties": properties
    }


def write_geojson(path, features):
    document = {
        "type": "FeatureCollection",
        "features": features
    }

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            document,
            file,
            ensure_ascii=False,
            separators=(",", ":")
        )


def representative_point(geometry):
    if isinstance(
        geometry,
        (LineString, MultiLineString)
    ):
        point = geometry.interpolate(
            geometry.length / 2
        )
    else:
        point = geometry.representative_point()

    return {
        "lat": round(point.y, 7),
        "lon": round(point.x, 7)
    }


def get_communes():
    """
    Fuente primaria: límites comunales MOP.
    Respaldo: DPA 2020 institucional publicada por MINVU.
    El respaldo se identifica explícitamente en properties y metadata.
    """
    source_url = URL_COMMUNES
    source_label = "MOP · Límites administrativos"
    source_status = "primary"

    try:
        features, fields, metadata = fetch_features(URL_COMMUNES)
    except Exception as primary_error:
        log(
            "MOP límites comunales no disponible; activando respaldo DPA institucional: "
            + str(primary_error)
        )
        source_url = URL_COMMUNES_FALLBACK
        source_label = (
            "IDE MINVU · DPA 2020 (SUBDERE, IGM, DIFROL e INE) · respaldo"
        )
        source_status = "fallback_dpa_2020"
        features, fields, metadata = fetch_features(
            URL_COMMUNES_FALLBACK
        )

    name_field = find_field(
        fields,
        [
            "NOM_COM",
            "COMUNA",
            "NOMBRE_COMUNA",
            "NOM_COMUNA"
        ]
    )

    if not name_field:
        raise RuntimeError(
            "No se encontró el campo de nombre comunal "
            "en la fuente administrativa seleccionada."
        )

    records = records_from_features(features)
    selected = {}

    for record in records:
        name = record["properties"].get(name_field)
        normalized = normalize(name)

        if normalized in TARGET_COMMUNES:
            selected[TARGET_COMMUNES[normalized]] = record

    missing = sorted(
        set(TARGET_COMMUNES.values()) - set(selected.keys())
    )

    if missing:
        raise RuntimeError(
            "La fuente administrativa seleccionada no permitió verificar "
            "todas las comunas objetivo. Faltan: "
            + ", ".join(missing)
            + ". No se publicarán datos parciales."
        )

    if len(selected) != EXPECTED_COMMUNES:
        raise RuntimeError(
            "La cantidad de comunas recuperadas no coincide "
            "con las nueve comunas objetivo."
        )

    output = []

    for display_name, record in sorted(selected.items()):
        geometry = record["geometry"]

        if geometry.is_empty or not geometry.is_valid:
            raise RuntimeError(
                "Geometría comunal inválida: "
                + display_name
            )

        props = record["properties"]

        output.append(
            geojson_feature(
                geometry,
                {
                    "name": display_name,
                    "official_id": props.get("OBJECTID") or props.get("FID"),
                    "commune_code": props.get("COD_COM") or props.get("CUT_COM"),
                    "province_code": props.get("CODMOP_PROV") or props.get("CUT_PROV"),
                    "source": source_label,
                    "source_status": source_status
                }
            )
        )

    source_info = {
        "institution": "MOP" if source_status == "primary" else "IDE MINVU / SUBDERE / IGM / DIFROL / INE",
        "url": source_url,
        "status": source_status,
        "primary_url": URL_COMMUNES,
        "fallback_url": URL_COMMUNES_FALLBACK,
        "note": (
            "MOP respondió correctamente."
            if source_status == "primary"
            else "Respaldo DPA 2020; antigüedad y procedencia identificadas. Validar antes de usar como cartografía oficial vigente."
        )
    }

    return output, records, metadata, source_info

def get_provinces(commune_records):
    commune_union = unary_union([
        record["geometry"]
        for record in commune_records
    ])

    # La capa provincial contiene pocos registros. Descargarla completa
    # evita enviar polígonos comunales extensos al servicio MOP, cuyo
    # endpoint ha agotado el tiempo de espera al recibir consultas POST.
    # El recorte exacto al territorio de las nueve comunas se realiza abajo.
    features, fields, metadata = fetch_features(
        URL_PROVINCES
    )

    records = records_from_features(features, "límites comunales")

    name_field = find_field(
        fields,
        [
            "NOM_PROV",
            "PROVINCIA",
            "NOMBRE_PROVINCIA"
        ]
    )

    output = []

    for record in records:
        geometry = record["geometry"]

        if not geometry.intersects(commune_union):
            continue

        clipped = geometry.intersection(commune_union)

        if clipped.is_empty:
            continue

        props = record["properties"]

        output.append(
            geojson_feature(
                clipped,
                {
                    "name": (
                        props.get(name_field)
                        if name_field else "Provincia"
                    ),
                    "official_id": props.get("OBJECTID"),
                    "source": "MOP · Límites administrativos"
                }
            )
        )

    if not output:
        raise RuntimeError(
            "No se pudieron construir las provincias."
        )

    return output, metadata


def query_water_layer(
    layer_url,
    source_name,
    water_type,
    commune_union
):
    # La consulta remota usa intersección poligonal exacta por comuna.
    features, fields, metadata = fetch_features(
        layer_url,
        geometry=commune_union
    )

    name_field = find_field(
        fields,
        [
            "NOMBRE",
            "NOMBRESS",
            "NOM_RIO",
            "NOM_CUERPO",
            "TOPONIMO",
            "TEXTO",
            "NOM"
        ]
    )

    type_field = find_field(
        fields,
        [
            "TIPO",
            "TIPO_ENT",
            "CLASE",
            "CATEGORIA",
            "CATEGORÍA"
        ]
    )
    basin_code_field = find_field(fields, ["COD_CUEN"])
    subbasin_code_field = find_field(fields, ["COD_SUBC"])
    subsubbasin_code_field = find_field(fields, ["COD_SSUBC"])

    records = records_from_features(features, source_name)
    output = []

    for record in records:
        geom = record["geometry"]

        # Filtro espacial exacto contra los límites comunales.
        if not geom.intersects(commune_union):
            continue

        clipped = geom.intersection(commune_union)

        if clipped.is_empty:
            continue

        props = record["properties"]

        source_feature_name = (
            props.get(name_field)
            if name_field else None
        )
        if not source_feature_name:
            source_feature_name = "Cuerpo de agua sin nombre"

        name = str(source_feature_name).strip()
        communes = sorted(set(
            commune["name"]
            for commune in intersecting_communes(clipped)
        ))

        # Corrección toponímica local para Tierra del Fuego:
        # el tramo rotulado "Río Serrano" dentro de Primavera corresponde
        # al Río del Oro. Se conserva el nombre de origen como alias.
        toponymy_status = "source_name"
        aliases = []
        if normalize(name) == "rio serrano" and "Primavera" in communes:
            aliases = [name]
            name = "Río del Oro"
            toponymy_status = "locally_corrected"

        subtype = (
            props.get(type_field)
            if type_field else None
        )

        official_id = props.get("OBJECTID")

        stable = (
            source_name
            + "|"
            + str(official_id)
            + "|"
            + normalize(name)
        )

        water_id = hashlib.sha1(
            stable.encode("utf-8")
        ).hexdigest()[:16]

        communes = [
            commune["name"]
            for commune in intersecting_communes(clipped)
        ]

        output.append(
            geojson_feature(
                clipped,
                {
                    "waterbody_id": water_id,
                    "name": name,
                    "source_name": str(source_feature_name).strip(),
                    "aliases": aliases,
                    "toponymy_status": toponymy_status,
                    "water_type": water_type,
                    "water_category": (
                        "river" if water_type in ("river", "river_or_stream")
                        else "lagoon" if (
                            "laguna" in normalize(name)
                            or "laguna" in normalize(subtype)
                        )
                        else "lake"
                    ),
                    "subtype": subtype,
                    "official_source": source_name,
                    "official_id": official_id,
                    "source_attributes": props,
                    "communes": communes,
                    "provinces": sorted(set(intersecting_provinces(clipped))),
                    "basin_code": props.get(basin_code_field) if basin_code_field else None,
                    "subbasin_code": props.get(subbasin_code_field) if subbasin_code_field else None,
                    "subsubbasin_code": props.get(subsubbasin_code_field) if subsubbasin_code_field else None,
                    "representative_point": representative_point(
                        clipped
                    ),
                    "geometry_status": "official_geometry",
                    "source_confidence": "official"
                }
            )
        )

    return output, metadata


def query_dga_hydro_units(layer_url, level, name_field_name, commune_union):
    """Descarga unidades BNA DGA y las recorta a las nueve comunas objetivo."""
    features, fields, metadata = fetch_features(layer_url, geometry=commune_union)
    name_field = find_field(fields, [name_field_name])
    code_field = find_field(fields, {
        "basin": ["COD_CUEN"],
        "subbasin": ["COD_SUBC"],
        "subsubbasin": ["COD_SSUBC"]
    }[level])
    records = records_from_features(features, "unidades hidrográficas DGA")
    output = []

    for record in records:
        geometry = record["geometry"]
        if not geometry.intersects(commune_union):
            continue
        clipped = geometry.intersection(commune_union)
        if clipped.is_empty:
            continue
        props = record["properties"]
        communes = sorted(set(
            item["name"] for item in intersecting_communes(clipped)
        ))
        output.append(geojson_feature(clipped, {
            "unit_id": level + "|" + str(props.get(code_field) or props.get("OBJECTID")),
            "unit_level": level,
            "name": str(props.get(name_field) or "Unidad hidrográfica sin nombre"),
            "code": props.get(code_field) if code_field else None,
            "basin_code": props.get("COD_CUEN"),
            "subbasin_code": props.get("COD_SUBC"),
            "subsubbasin_code": props.get("COD_SSUBC"),
            "communes": communes,
            "provinces": sorted(set(intersecting_provinces(clipped))),
            "official_source": "DGA · Banco Nacional de Aguas (capa IDE publicada por SMA)",
            "source_url": layer_url,
            "official_id": props.get("OBJECTID"),
            "source_attributes": props
        }))
    return output, metadata


def enrich_waterbodies_with_hydro_units(water_features, hydro_units):
    """Asocia cuencas y subunidades BNA mediante intersección espacial."""
    prepared = [
        (shape(feature["geometry"]), feature["properties"])
        for feature in hydro_units
    ]
    for feature in water_features:
        geometry = shape(feature["geometry"])
        matches = []
        for unit_geometry, props in prepared:
            if geometry.intersects(unit_geometry):
                matches.append({
                    "level": props.get("unit_level"),
                    "name": props.get("name"),
                    "code": props.get("code"),
                    "basin_code": props.get("basin_code"),
                    "subbasin_code": props.get("subbasin_code"),
                    "subsubbasin_code": props.get("subsubbasin_code")
                })
        feature["properties"]["hydro_units"] = matches
        for level, key in (
            ("basin", "basins"),
            ("subbasin", "subbasins"),
            ("subsubbasin", "subsubbasins")
        ):
            feature["properties"][key] = sorted({
                item["name"] for item in matches
                if item["level"] == level and item.get("name")
            })
    return water_features


def get_dga_stations(commune_union):
    # Recuperación de candidatos mediante bounding box.
    features, fields, metadata = fetch_features(
        URL_DGA_STATIONS,
        geometry=commune_union
    )

    records = records_from_features(features, "estaciones DGA")
    output = []

    for record in records:
        geom = record["geometry"]

        # Las estaciones se conservan solamente si están
        # dentro o intersectan el territorio comunal real.
        if not geom.intersects(commune_union):
            continue

        props = record["properties"]

        communes = [
            commune["name"]
            for commune in intersecting_communes(geom)
        ]

        output.append(
            geojson_feature(
                geom,
                {
                    "official_source": "DGA · Red Hidrométrica Nacional",
                    "official_id": props.get("OBJECTID"),
                    "communes": sorted(set(communes)),
                    "attributes": props
                }
            )
        )

    return output, metadata


def write_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def validate_geojson(path, minimum=1):
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("type") != "FeatureCollection":
        raise RuntimeError(
            "GeoJSON inválido: " + path.name
        )

    features = data.get("features", [])

    if len(features) < minimum:
        raise RuntimeError(
            "Cantidad insuficiente de elementos en "
            + path.name
        )

    for feature in features:
        if not feature.get("geometry"):
            raise RuntimeError(
                "Geometría vacía en " + path.name
            )

        geometry = shape(feature["geometry"])

        if geometry.is_empty:
            raise RuntimeError(
                "Geometría vacía en " + path.name
            )

        if not geometry.is_valid:
            raise RuntimeError(
                "Geometría inválida en " + path.name
            )

    return len(features)


def publish_atomically(temp_dir):
    DATA.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)

    files = [
        "communes.geojson",
        "provinces.geojson",
        "waterbodies.geojson",
        "dga_hydro_units.geojson",
        "dga_stations.geojson"
    ]

    for filename in files:
        source = temp_dir / filename

        if not source.exists():
            raise RuntimeError(
                "Falta archivo requerido: " + filename
            )

    metadata_source = temp_dir / "sources.json"

    if not metadata_source.exists():
        raise RuntimeError(
            "Falta archivo requerido: sources.json"
        )

    # Preparar todos los archivos antes de reemplazar
    # los archivos publicados.
    staged = []

    for filename in files:
        destination = DATA / filename
        staging = DATA / (filename + ".tmp")

        staging.write_bytes(
            (temp_dir / filename).read_bytes()
        )

        staged.append((staging, destination))

    metadata_destination = META / "sources.json"
    metadata_staging = META / "sources.json.tmp"

    metadata_staging.write_bytes(
        metadata_source.read_bytes()
    )

    staged.append((
        metadata_staging,
        metadata_destination
    ))

    # Reemplazo individual mediante rename en el mismo
    # sistema de archivos.
    for staging, destination in staged:
        staging.replace(destination)


def main():
    global COMMUNE_GEOMETRIES

    log("Inicio de AnglerMap Geodata 4.0")
    log("Territorio: nueve comunas de Magallanes.")
    log("Fuentes: MOP, IGM y DGA (drenajes, lagos y unidades BNA).")
    log("Cabo de Hornos y Antártica excluidos.")

    with TemporaryDirectory(
        prefix="anglermap-geodata-"
    ) as temporary:

        temp_dir = Path(temporary)

        # 1. Límites administrativos MOP
        log("Descargando límites comunales MOP")

        commune_features, commune_records, commune_meta, commune_source_info = (
            get_communes()
        )

        COMMUNE_GEOMETRIES = []

        for feature in commune_features:
            COMMUNE_GEOMETRIES.append({
                "name": feature["properties"]["name"],
                "geometry": shape(feature["geometry"])
            })

        commune_union = unary_union([
            item["geometry"]
            for item in COMMUNE_GEOMETRIES
        ])
        build_commune_spatial_index()

        write_geojson(
            temp_dir / "communes.geojson",
            commune_features
        )

        # 2. Provincias MOP para clasificar las aguas por provincia.
        global PROVINCE_GEOMETRIES
        try:
            province_features, province_meta = get_provinces([{"geometry": shape(item["geometry"])} for item in commune_features])
            PROVINCE_GEOMETRIES = [{
                "name": item["properties"]["name"],
                "geometry": shape(item["geometry"])
            } for item in province_features]
            write_geojson(temp_dir / "provinces.geojson", province_features)
            province_status = {"status": "available", "features": len(province_features)}
        except Exception as error:
            log("Capa provincial MOP no disponible: " + str(error))
            PROVINCE_GEOMETRIES = []
            province_meta = None
            province_features = []
            province_status = {"status": "unavailable", "reason": str(error)}
            write_geojson(temp_dir / "provinces.geojson", [])

        # 3. Hidrografía IGM
        log("Consultando hidrografía lineal IGM")

        igm_rivers, igm_rivers_meta = query_water_layer(
            URL_IGM_RIVERS,
            "IGM · Cartografía 1:50.000 · Hidrografía lineal",
            "river_or_stream",
            commune_union
        )

        log("Consultando hidrografía de áreas IGM")

        igm_lakes, igm_lakes_meta = query_water_layer(
            URL_IGM_WATERS,
            "IGM · Cartografía 1:50.000 · Hidrografía de áreas",
            "lake_or_lagoon",
            commune_union
        )

        # 4. Complemento hidrográfico MOP
        mop_rivers = []
        mop_lakes = []
        mop_status = {}

        try:
            log("Consultando ríos MOP")

            mop_rivers, mop_rivers_meta = query_water_layer(
                URL_MOP_RIVERS,
                "MOP · Red Hidrográfica · Ríos",
                "river",
                commune_union
            )

            mop_status["rivers"] = {
                "status": "available",
                "features": len(mop_rivers)
            }

        except Exception as error:
            log(
                "Fuente complementaria MOP ríos no disponible: "
                + str(error)
            )

            mop_status["rivers"] = {
                "status": "unavailable",
                "reason": str(error)
            }

        try:
            log("Consultando sistemas lacustres MOP")

            mop_lakes, mop_lakes_meta = query_water_layer(
                URL_MOP_LAKES,
                "MOP · Red Hidrográfica · Sistemas lacustres",
                "lake",
                commune_union
            )

            mop_status["lakes"] = {
                "status": "available",
                "features": len(mop_lakes)
            }

        except Exception as error:
            log(
                "Fuente complementaria MOP lagos no disponible: "
                + str(error)
            )

            mop_status["lakes"] = {
                "status": "unavailable",
                "reason": str(error)
            }

        # 4. Hidrografía DGA: drenajes, lagos y unidades BNA.
        dga_status = {}
        dga_rivers = []
        dga_lakes = []
        dga_hydro_units = []

        for key, url, label, water_type in (
            ("drainage", URL_DGA_DRAINAGE, "DGA · Red de drenajes", "river_or_stream"),
            ("lakes", URL_DGA_LAKES, "DGA · Inventario de lagos", "lake_or_lagoon")
        ):
            try:
                records, _metadata = query_water_layer(
                    url, label, water_type, commune_union
                )
                if key == "drainage":
                    dga_rivers = records
                else:
                    dga_lakes = records
                dga_status[key] = {"status": "available", "features": len(records)}
            except Exception as error:
                log("Fuente DGA " + key + " no disponible: " + str(error))
                dga_status[key] = {"status": "unavailable", "reason": str(error)}

        for level, url, field_name in (
            ("basin", URL_DGA_BASINS, "NOM_CUEN"),
            ("subbasin", URL_DGA_SUBBASINS, "NOM_SUBC"),
            ("subsubbasin", URL_DGA_SUBSUBBASINS, "NOM_SSUBC")
        ):
            try:
                records, _metadata = query_dga_hydro_units(
                    url, level, field_name, commune_union
                )
                dga_hydro_units.extend(records)
                dga_status[level] = {"status": "available", "features": len(records)}
            except Exception as error:
                log("Unidad BNA DGA " + level + " no disponible: " + str(error))
                dga_status[level] = {"status": "unavailable", "reason": str(error)}

        # IGM aporta detalle cartográfico; MOP y DGA complementan
        # geometría, nombres e inventario de unidades hidrográficas.
        all_waters = (
            igm_rivers + igm_lakes
            + mop_rivers + mop_lakes
            + dga_rivers + dga_lakes
        )
        all_waters = enrich_waterbodies_with_hydro_units(
            all_waters, dga_hydro_units
        )

        if not igm_rivers and not igm_lakes:
            raise RuntimeError(
                "IGM no entregó geometrías hidrográficas. "
                "No se publicarán archivos."
            )

        all_waters.sort(
            key=lambda item: (
                normalize(item["properties"]["name"]),
                item["properties"]["official_source"]
            )
        )

        write_geojson(
            temp_dir / "waterbodies.geojson",
            all_waters
        )
        write_geojson(
            temp_dir / "dga_hydro_units.geojson",
            dga_hydro_units
        )

        # 5. Estaciones DGA
        log("Descargando estaciones DGA")

        stations, dga_meta = get_dga_stations(
            commune_union
        )

        write_geojson(
            temp_dir / "dga_stations.geojson",
            stations
        )

        # 6. Validación
        log("Validando archivos generados")

        counts = {
            "communes": validate_geojson(
                temp_dir / "communes.geojson",
                EXPECTED_COMMUNES
            ),
            "provinces": validate_geojson(temp_dir / "provinces.geojson", 0),
            "waterbodies": validate_geojson(
                temp_dir / "waterbodies.geojson",
                1
            ),
            "dga_hydro_units": validate_geojson(
                temp_dir / "dga_hydro_units.geojson",
                0
            ),
            "dga_stations": validate_geojson(
                temp_dir / "dga_stations.geojson",
                0
            )
        }

        if counts["communes"] != EXPECTED_COMMUNES:
            raise RuntimeError(
                "La cobertura comunal no contiene exactamente "
                "las nueve comunas objetivo."
            )

        commune_names = sorted(
            feature["properties"]["name"]
            for feature in commune_features
        )

        if set(commune_names) != set(
            TARGET_COMMUNES.values()
        ):
            raise RuntimeError(
                "La cobertura comunal no coincide con "
                "el territorio definido."
            )

        metadata = {
            "application": "AnglerMap",
            "version": "3.4",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "geographic_scope": {
                "region": "Magallanes y de la Antártica Chilena",
                "communes": commune_names,
                "commune_count": EXPECTED_COMMUNES,
                "antarctica_commune_included": False,
                "cape_horn_commune_included": False
            },
            "spatial_query_method": {
                "remote_query": "exact_polygon_intersection_per_commune",
                "remote_geometry_type": "esriGeometryPolygon",
                "local_filter": "exact_intersection_and_clip_with_commune_union",
                "commune_spatial_index": "STRtree",
                "spatial_reference": "EPSG:4326"
            },
            "sources": {
                "administrative_boundaries": commune_source_info,
                "provinces": {
                    "institution": "MOP",
                    "url": URL_PROVINCES,
                    "status": province_status,
                    "metadata_available": province_meta is not None
                },
                "igm_rivers": {
                    "institution": "IGM",
                    "url": URL_IGM_RIVERS,
                    "status": "required"
                },
                "igm_water_areas": {
                    "institution": "IGM",
                    "url": URL_IGM_WATERS,
                    "status": "required"
                },
                "mop_rivers": {
                    "institution": "MOP",
                    "url": URL_MOP_RIVERS,
                    "status": mop_status.get("rivers")
                },
                "mop_lakes": {
                    "institution": "MOP",
                    "url": URL_MOP_LAKES,
                    "status": mop_status.get("lakes")
                },
                "dga_drainage": {
                    "institution": "DGA",
                    "url": URL_DGA_DRAINAGE,
                    "copyright": "DGA 2012 / MOP",
                    "status": dga_status.get("drainage")
                },
                "dga_lakes": {
                    "institution": "DGA",
                    "url": URL_DGA_LAKES,
                    "copyright": "DGA 2017",
                    "status": dga_status.get("lakes")
                },
                "dga_basin_units": {
                    "institution": "DGA / Banco Nacional de Aguas",
                    "urls": {
                        "basins": URL_DGA_BASINS,
                        "subbasins": URL_DGA_SUBBASINS,
                        "subsubbasins": URL_DGA_SUBSUBBASINS
                    },
                    "status": {
                        "basin": dga_status.get("basin"),
                        "subbasin": dga_status.get("subbasin"),
                        "subsubbasin": dga_status.get("subsubbasin")
                    }
                },
                "dga_stations": {
                    "institution": "DGA",
                    "url": URL_DGA_STATIONS,
                    "status": "required"
                }
            },
            "counts": counts,
            "limitations": [
                "La presencia de una geometría oficial no acredita acceso público ni permiso de pesca.",
                "Las capas hidrográficas pueden no contener todos los cuerpos de agua existentes.",
                "Las fuentes hidrográficas se conservan identificadas por procedencia; nombres homónimos no se fusionan si sus geometrías difieren.",
                "La asociación de cuencas, subcuencas y subsubcuencas se calcula por intersección espacial con unidades BNA DGA.",
                "La asociación a provincia depende de la disponibilidad de la capa provincial MOP.",
                "La comuna Antártica queda excluida.",
                "La comuna de Cabo de Hornos queda excluida del alcance inicial.",
                "Las estaciones DGA son puntos de monitoreo; este archivo no representa por sí solo mediciones hidrométricas en tiempo real."
            ]
        }

        write_json(
            temp_dir / "sources.json",
            metadata
        )

        # Validación final de metadata
        with (temp_dir / "sources.json").open(
            "r",
            encoding="utf-8"
        ) as file:
            json.load(file)

        # 7. Publicación
        log("Publicando archivos validados")

        publish_atomically(temp_dir)

        log("Publicación de archivos completada.")
        log(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        log("ERROR: " + str(error))
        raise
