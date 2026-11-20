
import hashlib
import json
import re
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
    LinearRing
)
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "magallanes"
META = ROOT / "data" / "metadata"

BASE = "https://rest-sit.mop.gob.cl/arcgis/rest/services"

URL_COMMUNES = BASE + "/MAPA_BASE/LIMITES/MapServer/2"
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
MAX_RETRIES = 3

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AnglerMap-Geodata/3.0"
})

COMMUNE_GEOMETRIES = []


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


def request_json(url, params=None):
    params = dict(params or {})
    params.setdefault("f", "json")

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = SESSION.get(
                url,
                params=params,
                timeout=(15, 60)
            )

            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    "HTTP " + str(response.status_code)
                )

            response.raise_for_status()

            data = response.json()

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


def fetch_ids(layer_url, where="1=1", geometry=None):
    """
    Recupera IDs candidatos desde ArcGIS.

    Si se proporciona una geometría Shapely, se consulta
    utilizando exclusivamente su bounding box.

    El filtro espacial exacto se realiza posteriormente
    en Python contra las geometrías comunales reales.
    """

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
            "spatialReference": {
                "wkid": 4326
            }
        }

        params.update({
            "geometry": json.dumps(
                envelope,
                separators=(",", ":")
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects"
        })

    data = request_json(
        layer_url + "/query",
        params
    )

    return data.get("objectIds") or []


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
        }
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


def records_from_features(features):
    output = []

    for feature in features:
        geometry = esri_to_shape(
            feature.get("geometry")
        )

        if geometry is None or geometry.is_empty:
            continue

        output.append({
            "geometry": geometry,
            "properties": feature.get("attributes") or {}
        })

    return output


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
    features, fields, metadata = fetch_features(
        URL_COMMUNES
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
            "en la capa MOP."
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
            "La fuente MOP no permitió verificar todas "
            "las comunas objetivo. Faltan: "
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
                    "official_id": props.get("OBJECTID"),
                    "commune_code": props.get("COD_COM"),
                    "province_code": props.get("CODMOP_PROV"),
                    "source": "MOP · Límites administrativos"
                }
            )
        )

    return output, records, metadata


def get_provinces(commune_records):
    commune_union = unary_union([
        record["geometry"]
        for record in commune_records
    ])

    features, fields, metadata = fetch_features(
        URL_PROVINCES,
        geometry=commune_union
    )

    records = records_from_features(features)

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
    # La consulta remota utiliza solamente el bounding box.
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
            "CATEGORIA"
        ]
    )

    records = records_from_features(features)
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

        name = (
            props.get(name_field)
            if name_field else None
        )

        if not name:
            name = "Cuerpo de agua sin nombre"

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

        communes = []

        for commune in COMMUNE_GEOMETRIES:
            if clipped.intersects(commune["geometry"]):
                communes.append(commune["name"])

        output.append(
            geojson_feature(
                clipped,
                {
                    "waterbody_id": water_id,
                    "name": str(name).strip(),
                    "water_type": water_type,
                    "subtype": subtype,
                    "official_source": source_name,
                    "official_id": official_id,
                    "communes": sorted(set(communes)),
                    "representative_point": representative_point(
                        clipped
                    ),
                    "geometry_status": "official_geometry",
                    "source_confidence": "official"
                }
            )
        )

    return output, metadata


def get_dga_stations(commune_union):
    # Recuperación de candidatos mediante bounding box.
    features, fields, metadata = fetch_features(
        URL_DGA_STATIONS,
        geometry=commune_union
    )

    records = records_from_features(features)
    output = []

    for record in records:
        geom = record["geometry"]

        # Las estaciones se conservan solamente si están
        # dentro o intersectan el territorio comunal real.
        if not geom.intersects(commune_union):
            continue

        props = record["properties"]

        communes = []

        for commune in COMMUNE_GEOMETRIES:
            if geom.intersects(commune["geometry"]):
                communes.append(commune["name"])

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

    log("Inicio de AnglerMap Geodata 3.0")
    log("Territorio: nueve comunas de Magallanes.")
    log("Fuentes: MOP, IGM y DGA. SNIA excluido.")
    log("Cabo de Hornos y Antártica excluidos.")

    with TemporaryDirectory(
        prefix="anglermap-geodata-"
    ) as temporary:

        temp_dir = Path(temporary)

        # 1. Límites administrativos MOP
        log("Descargando límites comunales MOP")

        commune_features, commune_records, commune_meta = (
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

        write_geojson(
            temp_dir / "communes.geojson",
            commune_features
        )

        # 2. Provincias MOP
        log("Construyendo provincias")

        province_features, province_meta = get_provinces(
            commune_records
        )

        write_geojson(
            temp_dir / "provinces.geojson",
            province_features
        )

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

        # IGM se conserva como fuente principal de geometría
        # detallada. MOP queda como complemento separado.
        all_waters = (
            igm_rivers
            + igm_lakes
            + mop_rivers
            + mop_lakes
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
            "provinces": validate_geojson(
                temp_dir / "provinces.geojson",
                1
            ),
            "waterbodies": validate_geojson(
                temp_dir / "waterbodies.geojson",
                1
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
            "version": "3.0",
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
                "remote_query": "bounding_box",
                "remote_geometry_type": "esriGeometryEnvelope",
                "local_filter": "exact_intersection_with_commune_geometries",
                "spatial_reference": "EPSG:4326"
            },
            "sources": {
                "administrative_boundaries": {
                    "institution": "MOP",
                    "url": URL_COMMUNES,
                    "status": "required"
                },
                "provinces": {
                    "institution": "MOP",
                    "url": URL_PROVINCES,
                    "status": "required"
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
                "Las geometrías de fuentes diferentes se conservan identificadas por separado hasta realizar conciliación de entidades.",
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
