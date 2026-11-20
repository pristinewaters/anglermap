
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

# Una fuente institucional por temática: MOP para caminos y DGA para aguas.
# MOP Dirección de Vialidad: red vial nacional (incluye caminos regionales
# comunales y caminos regionales de acceso). La capa 3 es la de mayor detalle.
URL_MOP_ROADS = (
    BASE + "/VIALIDAD/Red_Vial_Chile_Base_gris/MapServer/3"
)

# Servicio hidrográfico DGA publicado en IDE SMA: dos subcapas que se
# consolidan en un único GeoJSON de cuerpos de agua.
URL_DGA_IDE = "https://ideserver.sma.gob.cl/arcgis/rest/services/IDE/Recursos_hidricos_glaciares/MapServer"
URL_DGA_DRAINAGE = URL_DGA_IDE + "/2"
URL_DGA_LAKES = URL_DGA_IDE + "/5"
# Red Hidrométrica Nacional DGA: inventario puntual de estaciones de distintos tipos.
URL_DGA_STATIONS = BASE + "/DGA/Red_Hidrometrica/MapServer/0"
# Datos operacionales de estaciones fluviométricas (SNIA), para enriquecer popups.
URL_DGA_LIVE_FLOW = "https://services3.arcgis.com/aSoEm9TBK2shtWjP/ArcGIS/rest/services/DGA_MONITOREO_CAUCE/FeatureServer/0"


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

# Relación administrativa oficial comuna → provincia, usada como respaldo
# si la capa geométrica provincial MOP no está disponible.
BATCH_SIZE = 100
MAX_RETRIES = 4

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AnglerMap-Geodata/3.3"
})

COMMUNE_GEOMETRIES = []
COMMUNE_TREE = None
COMMUNE_TREE_LOOKUP = {}


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

def clean_source_attributes(properties):
    """Conserva atributos de origen útiles, excluyendo códigos de cuencas."""
    excluded = {
        "cod_cuen", "cod_subc", "cod_ssubc", "codbna",
        "cod_bna", "nom_cuen", "nom_subc", "nom_ssubc",
        "supcuen", "suphoya"
    }
    return {
        key: value
        for key, value in (properties or {}).items()
        if normalize(key) not in excluded
    }


def query_water_layer(layer_url, source_name, water_type, commune_union):
    """Descarga y recorta una subcapa DGA de drenajes o lagos."""
    features, fields, metadata = fetch_features(
        layer_url,
        geometry=commune_union
    )
    name_field = find_field(fields, ["NOMBRE", "NOM", "TOPONIMO"])
    type_field = find_field(fields, ["TIPO", "CATEGORIA", "CLASIFICAC"])
    records = records_from_features(features, source_name)
    output = []

    for record in records:
        geometry = record["geometry"]
        if not geometry.intersects(commune_union):
            continue
        clipped = geometry.intersection(commune_union)
        if clipped.is_empty:
            continue

        props = record["properties"]
        raw_name = props.get(name_field) if name_field else None
        name = str(raw_name or "").strip()
        if not name:
            # No inventar topónimos. La geometría anónima permanece en el
            # GeoJSON para representación, pero no se convierte en entrada
            # nominal del catálogo.
            name = "Cuerpo de agua sin nombre"

        communes = sorted({
            item["name"] for item in intersecting_communes(clipped)
        })
        subtype = props.get(type_field) if type_field else None
        subtype_text = str(subtype or "").strip()
        subtype_normalized = normalize(subtype_text)

        if water_type == "river":
            # No se filtra la red lineal DGA: se conserva cada elemento
            # con nombre y tipo de origen. La etiqueta visible respeta TIPO.
            category = "river"
            if "rio" in subtype_normalized:
                category_label = "Río"
            elif "estero" in subtype_normalized:
                category_label = "Estero"
            elif "chorrillo" in subtype_normalized:
                category_label = "Chorrillo"
            elif "arroyo" in subtype_normalized:
                category_label = "Arroyo"
            elif "quebrada" in subtype_normalized:
                category_label = "Quebrada"
            elif "canal" in subtype_normalized:
                category_label = "Canal"
            else:
                category_label = "Curso de agua"
        else:
            # La capa DGA 5 es el inventario poligonal nacional de lagos.
            # Se respeta el campo TIPO; el nombre solo sirve como respaldo
            # cuando el atributo de clasificación viene vacío.
            lagoon_by_name = normalize(name).startswith("laguna ")
            category = (
                "lagoon"
                if "laguna" in subtype_normalized
                or (not subtype_normalized and lagoon_by_name)
                else "lake"
            )
            category_label = "Laguna" if category == "lagoon" else "Lago"

        source_feature_name = name
        aliases = []
        toponymy_status = "source_name"
        toponymy_note = None

        official_id = props.get("OBJECTID")
        stable = source_name + "|" + str(official_id) + "|" + normalize(name)
        water_id = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]

        for commune in COMMUNE_GEOMETRIES:
            if commune["name"] not in communes:
                continue
            segment = clipped.intersection(commune["geometry"])
            if segment.is_empty:
                continue
            output.append(geojson_feature(segment, {
                "waterbody_id": water_id,
                "name": name,
                "source_name": source_feature_name,
                "aliases": aliases,
                "toponymy_status": toponymy_status,
                "toponymy_note": toponymy_note,
                "water_type": category,
                "water_category": category,
                "category_label": category_label,
                "subtype": subtype_text or None,
                "official_source": "DGA · " + source_name,
                "official_id": official_id,
                "source_attributes": clean_source_attributes(props),
                "communes": [commune["name"]],
                "representative_point": representative_point(segment),
                "geometry_status": "official_geometry",
                "source_confidence": "official"
            }))

    return output, metadata


def query_dga_stations(commune_union):
    """Descarga la Red Hidrométrica Nacional DGA como puntos independientes."""
    features, fields, metadata = fetch_features(
        URL_DGA_STATIONS,
        geometry=commune_union
    )
    records = records_from_features(features, "estaciones Red Hidrométrica DGA")
    output = []

    for record in records:
        geometry = record["geometry"]
        if not geometry.intersects(commune_union):
            continue
        props = record["properties"]
        communes = sorted({
            item["name"] for item in intersecting_communes(geometry)
        })
        if not communes:
            continue

        station_id = props.get("ID_IDE") or props.get("OBJECTID")
        output.append(geojson_feature(geometry, {
            "station_id": str(station_id) if station_id is not None else None,
            "station_name": props.get("NOM_ESTACION") or "Estación DGA sin nombre",
            "station_type": props.get("TIPO_ESTACION"),
            "vigencia": props.get("VIGENCIA"),
            "place": props.get("LUGAR"),
            "associated_lake": props.get("LAGO_ASOCIADO"),
            "communes": communes,
            "official_source": "DGA · Red Hidrométrica Nacional",
            "source_url": URL_DGA_STATIONS,
            "source_updated": "Julio 2022 según metadata del servicio",
            "source_attributes": props
        }))

    return output, metadata


def query_mop_roads(commune_union):
    """Descarga caminos MOP y genera una única capa GeoJSON de accesos."""
    features, fields, metadata = fetch_features(
        URL_MOP_ROADS,
        geometry=commune_union
    )
    records = records_from_features(features, "MOP · Red vial")
    output = []
    for record in records:
        geometry = record["geometry"]
        if not geometry.intersects(commune_union):
            continue
        clipped = geometry.intersection(commune_union)
        if clipped.is_empty:
            continue
        props = record["properties"]
        communes = sorted({
            item["name"] for item in intersecting_communes(clipped)
        })
        for commune in COMMUNE_GEOMETRIES:
            if commune["name"] not in communes:
                continue
            segment = clipped.intersection(commune["geometry"])
            if segment.is_empty:
                continue
            output.append(geojson_feature(segment, {
                "road_id": str(props.get("OBJECTID") or props.get("GlobalID") or ""),
                "name": props.get("NOMBRE_CAMINO") or props.get("ROL_LABEL") or props.get("ROL") or "Camino sin nombre",
                "route_code": props.get("ROL"),
                "classification": props.get("CLASIFICACION"),
                "surface": props.get("CARPETA"),
                "status": props.get("RVO"),
                "communes": [commune["name"]],
                "official_source": "MOP · Dirección de Vialidad · Red Vial Chile Base Gris",
                "source_url": URL_MOP_ROADS,
                "source_attributes": props
            }))
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
        "roads.geojson",
        "waterbodies.geojson",
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

    log("AnglerMap Geodata · tres capas temáticas")
    log("MOP: caminos y accesos · DGA: cuerpos de agua · DGA: estaciones de monitoreo.")
    log("Territorio: nueve comunas de Magallanes; Antártica y Cabo de Hornos excluidos.")

    with TemporaryDirectory(prefix="anglermap-geodata-") as temporary:
        temp_dir = Path(temporary)

        # Los límites comunales MOP son geometría auxiliar para recortar
        # las tres capas temáticas; no se publican como capa de contenido.
        log("Descargando límites comunales MOP para el recorte territorial")
        commune_features, commune_records, commune_meta, commune_source_info = get_communes()
        COMMUNE_GEOMETRIES = [{
            "name": feature["properties"]["name"],
            "geometry": shape(feature["geometry"])
        } for feature in commune_features]
        commune_union = unary_union([item["geometry"] for item in COMMUNE_GEOMETRIES])
        build_commune_spatial_index()

        commune_names = sorted(item["name"] for item in COMMUNE_GEOMETRIES)
        if len(commune_names) != EXPECTED_COMMUNES or set(commune_names) != set(TARGET_COMMUNES.values()):
            raise RuntimeError("Los límites MOP no coinciden con las nueve comunas objetivo.")

        # Capa 1: caminos y accesos MOP.
        log("Descargando caminos y accesos MOP")
        roads, roads_meta = query_mop_roads(commune_union)
        write_geojson(temp_dir / "roads.geojson", roads)

        # Capa 2: cuerpos de agua DGA. Dos subcapas del mismo servicio
        # oficial se consolidan en un único inventario homogéneo.
        log("Descargando red de drenajes DGA")
        dga_rivers, drainage_meta = query_water_layer(
            URL_DGA_DRAINAGE,
            "Red de drenajes",
            "river",
            commune_union
        )
        log("Descargando inventario de lagos DGA")
        dga_lakes, lakes_meta = query_water_layer(
            URL_DGA_LAKES,
            "Inventario de lagos",
            "lake",
            commune_union
        )
        waters = dga_rivers + dga_lakes
        waters.sort(key=lambda feature: (
            normalize(feature["properties"]["name"]),
            feature["properties"]["water_category"],
            feature["properties"]["communes"][0]
        ))
        write_geojson(temp_dir / "waterbodies.geojson", waters)

        # Capa 3: estaciones DGA. Son puntos de monitoreo independientes;
        # no se utilizan sus nombres para nombrar ni crear cuerpos de agua.
        log("Descargando Red Hidrométrica Nacional DGA")
        stations, stations_meta = query_dga_stations(commune_union)
        write_geojson(temp_dir / "dga_stations.geojson", stations)

        counts = {
            "roads": validate_geojson(temp_dir / "roads.geojson", 1),
            "waterbodies": validate_geojson(temp_dir / "waterbodies.geojson", 1),
            "dga_stations": validate_geojson(temp_dir / "dga_stations.geojson", 1)
        }
        if not roads:
            raise RuntimeError("MOP no entregó caminos para el territorio objetivo.")
        if not waters:
            raise RuntimeError("DGA no entregó cuerpos de agua para el territorio objetivo.")

        # Los conteos del catálogo cuentan entidades DGA únicas, no
        # segmentos comunales: un río que cruza tres comunas es una entidad.
        category_ids = {}
        commune_category_ids = {}
        unnamed_segments = 0
        for feature in waters:
            props = feature["properties"]
            category = props["water_category"]
            water_id = props["waterbody_id"]
            category_ids.setdefault(category, set()).add(water_id)
            commune = props["communes"][0]
            commune_category_ids.setdefault(commune, {})
            commune_category_ids[commune].setdefault(category, set()).add(water_id)
            if props["name"] == "Cuerpo de agua sin nombre":
                unnamed_segments += 1

        category_counts = {
            category: len(ids)
            for category, ids in sorted(category_ids.items())
        }
        commune_counts = {
            commune: {
                category: len(ids)
                for category, ids in sorted(categories.items())
            }
            for commune, categories in sorted(commune_category_ids.items())
        }
        unique_waterbody_count = len({
            feature["properties"]["waterbody_id"] for feature in waters
        })

        road_commune_counts = {}
        for feature in roads:
            commune = feature["properties"]["communes"][0]
            road_commune_counts[commune] = road_commune_counts.get(commune, 0) + 1

        station_commune_counts = {}
        station_type_counts = {}
        for feature in stations:
            props = feature["properties"]
            station_type = props.get("station_type") or "Sin tipo informado"
            station_type_counts[station_type] = station_type_counts.get(station_type, 0) + 1
            for commune in props.get("communes", []):
                station_commune_counts[commune] = station_commune_counts.get(commune, 0) + 1

        metadata = {
            "application": "AnglerMap",
            "version": "5.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "geographic_scope": {
                "region": "Magallanes y de la Antártica Chilena",
                "communes": commune_names,
                "commune_count": EXPECTED_COMMUNES,
                "antarctica_commune_included": False,
                "cape_horn_commune_included": False
            },
            "architecture": {
                "roads": "Capa MOP de caminos y accesos.",
                "waterbodies": "Capa cartográfica DGA de cuerpos de agua: drenajes lineales y lagos poligonales.",
                "dga_stations": "Capa puntual DGA de estaciones de la Red Hidrométrica Nacional; separada de los cuerpos de agua.",
                "basins_subbasins": "Fuera de alcance.",
                "igm_hydrography": "Fuera de alcance."
            },
            "sources": {
                "administrative_clip_boundaries": commune_source_info,
                "roads": {
                    "institution": "MOP · Dirección de Vialidad",
                    "name": "Red Vial Chile Base Gris · capa de caminos de mayor detalle",
                    "url": URL_MOP_ROADS,
                    "metadata": "https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Red_Vial_Chile_Base_gris/MapServer/3",
                    "status": "available",
                    "data_vintage_note": "La ficha del servicio describe datos disponibles a enero de 2021; no equivale a confirmación en terreno de transitabilidad actual."
                },
                "waterbodies": {
                    "institution": "DGA",
                    "service": URL_DGA_IDE,
                    "drainage_layer": URL_DGA_DRAINAGE,
                    "lakes_layer": URL_DGA_LAKES,
                    "status": "available",
                    "drainage_copyright": "DGA 2012 / MOP",
                    "lakes_copyright": "DGA 2017",
                    "method": "Todos los registros intersectantes de las dos subcapas se conservan y se asignan por intersección geométrica a las comunas."
                },
                "dga_stations": {
                    "institution": "DGA · División de Hidrología",
                    "service": URL_DGA_STATIONS,
                    "operational_flow_data_service": URL_DGA_LIVE_FLOW,
                    "status": "available",
                    "station_inventory_note": "Red Hidrométrica Nacional con estaciones fluviométricas, calidad de aguas, meteorológicas, niveles de lagos y embalses, sedimentometría, pozos, nivometría y glaciología. Metadata del servicio cartográfico: actualización julio 2022."
                }
            },
            "counts": {
                **counts,
                "waterbodies_unique_entities": unique_waterbody_count,
                "waterbodies_unnamed_segments": unnamed_segments,
                "waterbodies_by_category": category_counts,
                "waterbodies_by_commune": commune_counts,
                "roads_by_commune": road_commune_counts,
                "dga_stations_by_commune": station_commune_counts,
                "dga_stations_by_type": station_type_counts
            },
            "toponymy_notes": [],
            "limitations": [
                "La red de drenajes DGA representa la mayoría de las expresiones espaciales de drenaje, no necesariamente todas.",
                "El inventario poligonal DGA de lagos se publica como dato 2017; puede no incluir todas las lagunas menores.",
                "La red vial MOP es cartografía oficial, pero no confirma transitabilidad, mantención, barreras, permisos ni acceso público actual.",
                "La presencia de un camino no acredita derecho de paso ni acceso legal a una propiedad.",
                "La presencia de un cuerpo de agua no acredita acceso público ni permiso de pesca.",
                "Las estaciones DGA son puntos de monitoreo; sus nombres no definen el nombre del río o lago donde se encuentran.",
                "La Red Hidrométrica Nacional publicada en la capa cartográfica consultada tiene metadata de actualización julio 2022; validar vigencia de cada estación antes de interpretar su operación."
            ]
        }
        write_json(temp_dir / "sources.json", metadata)
        with (temp_dir / "sources.json").open("r", encoding="utf-8") as file:
            json.load(file)

        publish_atomically(temp_dir)
        log("Publicación de las tres capas completada.")
        log(json.dumps(metadata["counts"], ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        log("ERROR: " + str(error))
        raise
