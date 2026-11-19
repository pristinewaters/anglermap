
import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from shapely.geometry import (
    shape,
    mapping,
    LineString,
    MultiLineString,
    box
)
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "magallanes"
META = ROOT / "data" / "metadata"

DATA.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)

BASE = "https://rest-sit.mop.gob.cl/arcgis/rest/services"

URL_CAUCE = BASE + "/SNIA/SNIA_CAUCES/MapServer/0"
URL_COMUNA = BASE + "/MAPA_BASE/LIMITES/MapServer/2"
URL_PROVINCIA = BASE + "/MAPA_BASE/LIMITES/MapServer/1"
URL_LAGOS = BASE + "/MAPA_BASE/RED_HIDROGRAFICA/MapServer/17"

# Cobertura continental utilizada en esta primera etapa.
# La comuna Antártica queda pendiente de una consulta geográfica específica.
REGION_BOUNDS = box(-76.5, -56.2, -65.5, -48.0)

BATCH_SIZE = 10
MAX_RETRIES = 4

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AnglerMap-Geodata/1.1"
})


def log(message):
    print("[AnglerMap] " + str(message), flush=True)


def normalize(value):
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(
        char for char in value
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", value)


def arcgis_request(url, params):
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = SESSION.get(
                url + "/query",
                params=params,
                timeout=(20, 120)
            )

            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    "HTTP " + str(response.status_code)
                )

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                error = data["error"]
                raise RuntimeError(
                    "ArcGIS "
                    + str(error.get("code"))
                    + ": "
                    + json.dumps(error, ensure_ascii=False)
                )

            return data

        except (
            requests.RequestException,
            ValueError,
            RuntimeError
        ) as error:
            last_error = error

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                log(
                    "Consulta fallida. Reintento "
                    + str(attempt + 1)
                    + "/"
                    + str(MAX_RETRIES - 1)
                    + " en "
                    + str(wait)
                    + " segundos. Motivo: "
                    + str(error)
                )
                time.sleep(wait)

    raise RuntimeError(
        "No fue posible consultar ArcGIS después de "
        + str(MAX_RETRIES)
        + " intentos: "
        + str(last_error)
    )


def fetch_batch(layer_url, object_ids):
    """
    Descarga un grupo pequeño de IDs.
    Si el servidor sigue fallando, divide el grupo
    en dos y vuelve a intentarlo.
    """

    if not object_ids:
        return []

    params = {
        "objectIds": ",".join(map(str, object_ids)),
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json"
    }

    try:
        data = arcgis_request(layer_url, params)

        if data.get("exceededTransferLimit"):
            raise RuntimeError(
                "ArcGIS indicó exceededTransferLimit"
            )

        features = data.get("features", [])

        received_ids = {
            str(
                feature.get("attributes", {}).get("OBJECTID")
            )
            for feature in features
        }

        expected_ids = set(map(str, object_ids))

        missing_ids = expected_ids - received_ids

        if missing_ids:
            raise RuntimeError(
                "ArcGIS no devolvió todos los registros. "
                "IDs pendientes: "
                + ", ".join(sorted(missing_ids))
            )

        return features

    except Exception as error:
        if len(object_ids) == 1:
            raise RuntimeError(
                "No se pudo descargar el registro "
                + str(object_ids[0])
                + " desde "
                + layer_url
                + ". Motivo: "
                + str(error)
            )

        middle = len(object_ids) // 2

        first_half = object_ids[:middle]
        second_half = object_ids[middle:]

        log(
            "Dividiendo grupo de "
            + str(len(object_ids))
            + " registros por error del servidor."
        )

        first_features = fetch_batch(
            layer_url,
            first_half
        )

        second_features = fetch_batch(
            layer_url,
            second_half
        )

        return first_features + second_features


def fetch_features(layer_url, where="1=1"):
    log("Consultando capa: " + layer_url)
    log("Filtro: " + where)

    ids_data = arcgis_request(layer_url, {
        "where": where,
        "returnIdsOnly": "true",
        "f": "json"
    })

    object_ids = ids_data.get("objectIds") or []

    if not object_ids:
        log("No se encontraron registros.")
        return []

    object_ids = sorted(set(object_ids))

    log(
        "Registros identificados: "
        + str(len(object_ids))
    )

    features = []

    for start in range(0, len(object_ids), BATCH_SIZE):
        batch = object_ids[start:start + BATCH_SIZE]

        batch_features = fetch_batch(
            layer_url,
            batch
        )

        features.extend(batch_features)

        log(
            "Descargados "
            + str(len(features))
            + " de "
            + str(len(object_ids))
        )

        time.sleep(0.15)

    if len(features) != len(object_ids):
        raise RuntimeError(
            "Descarga incompleta en "
            + layer_url
            + ". Esperados: "
            + str(len(object_ids))
            + ", recibidos: "
            + str(len(features))
        )

    return features


def esri_geometry_to_shape(geometry):
    if not geometry:
        return None

    if "paths" in geometry:
        paths = geometry["paths"]

        if not paths:
            return None

        if len(paths) == 1:
            geom = LineString(paths[0])
        else:
            geom = MultiLineString(paths)

    elif "rings" in geometry:
        geom = shape({
            "type": "Polygon",
            "coordinates": geometry["rings"]
        })

        if not geom.is_valid:
            geom = geom.buffer(0)

    else:
        return None

    if geom.is_empty:
        return None

    return geom


def feature_records(features):
    result = []

    for feature in features:
        attributes = feature.get("attributes") or {}

        geometry = esri_geometry_to_shape(
            feature.get("geometry")
        )

        if geometry is None or geometry.is_empty:
            continue

        result.append({
            "properties": attributes,
            "geometry": geometry
        })

    return result


def save_geojson(filename, features):
    document = {
        "type": "FeatureCollection",
        "features": features
    }

    path = DATA / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            document,
            file,
            ensure_ascii=False,
            separators=(",", ":")
        )

    log(
        "Guardado "
        + str(path.relative_to(ROOT))
        + " · "
        + str(len(features))
        + " elementos"
    )


def bounds_filter(records):
    return [
        record
        for record in records
        if record["geometry"].intersects(REGION_BOUNDS)
    ]


def build_admin_layer(url, name_field, output):
    records = feature_records(
        fetch_features(url)
    )

    records = bounds_filter(records)

    features = []

    for record in records:
        geom = record["geometry"].simplify(
            0.00002,
            preserve_topology=True
        )

        props = record["properties"]

        features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "name": props.get(name_field),
                "official_id": props.get("OBJECTID"),
                "source": "MOP · Límites administrativos"
            }
        })

    save_geojson(output, features)

    return records


def water_type_from_river(props):
    value = normalize(props.get("TIPO"))

    if "estero" in value or "quebrada" in value:
        return "stream"

    return "river"


def representative_point(geometry):
    if isinstance(geometry, (LineString, MultiLineString)):
        point = geometry.interpolate(
            geometry.length / 2
        )
    else:
        point = geometry.representative_point()

    return {
        "lat": round(point.y, 7),
        "lon": round(point.x, 7)
    }


def build_water_records(records, source, water_type, communes):
    grouped = {}

    for record in records:
        props = record["properties"]
        geom = record["geometry"]

        primary_name = (
            props.get("NOMBRE")
            or props.get("NOMBRESS")
            or ""
        ).strip()

        alternate_name = (
            props.get("NOMBRESS")
            or props.get("NOMBRE")
            or ""
        ).strip()

        official_id = props.get("OBJECTID")

        name = primary_name or "Cauce sin nombre"

        if source == "DGA/SNIA":
            kind = water_type_from_river(props)
            basin = str(props.get("CODCUEN") or "")
            subtype = str(props.get("TIPO") or "")
        else:
            kind = water_type
            basin = ""
            subtype = str(props.get("TIPO") or "")

        group_key = (
            normalize(name),
            basin,
            kind
        )

        if name == "Cauce sin nombre":
            group_key += (str(official_id),)

        if group_key not in grouped:
            grouped[group_key] = {
                "name": name,
                "alternates": set(),
                "geometries": [],
                "official_ids": [],
                "basin": basin,
                "kind": kind,
                "subtype": subtype
            }

        group = grouped[group_key]

        if alternate_name and alternate_name != name:
            group["alternates"].add(alternate_name)

        group["geometries"].append(geom)
        group["official_ids"].append(official_id)

    output = []

    for key, group in grouped.items():
        geometry = unary_union(group["geometries"])

        if geometry.is_empty:
            continue

        geometry = geometry.simplify(
            0.000015,
            preserve_topology=True
        )

        if geometry.is_empty:
            continue

        water_communes = []

        for commune in communes:
            if geometry.intersects(commune["geometry"]):
                commune_name = (
                    commune["properties"].get("NOM_COM")
                )

                if commune_name:
                    water_communes.append(commune_name)

        water_communes = sorted(set(water_communes))

        source_ids = sorted(
            set(
                str(value)
                for value in group["official_ids"]
                if value is not None
            )
        )

        stable_key = (
            source
            + "|"
            + "|".join(map(str, key))
        )

        water_id = hashlib.sha1(
            stable_key.encode("utf-8")
        ).hexdigest()[:16]

        output.append({
            "type": "Feature",
            "geometry": mapping(geometry),
            "properties": {
                "waterbody_id": water_id,
                "name": group["name"],
                "alternate_names": sorted(
                    group["alternates"]
                ),
                "water_type": group["kind"],
                "subtype": group["subtype"],
                "official_source": source,
                "official_ids": source_ids,
                "basin_code": group["basin"],
                "communes": water_communes,
                "representative_point": representative_point(
                    geometry
                ),
                "geometry_status": "official_geometry",
                "source_confidence": "official"
            }
        })

    return output


def main():
    log("Inicio de construcción cartográfica")

    # 1. Comunas
    log("Descargando límites comunales")

    communes = feature_records(
        fetch_features(URL_COMUNA)
    )

    communes = bounds_filter(communes)

    commune_features = []

    for record in communes:
        props = record["properties"]

        geom = record["geometry"].simplify(
            0.00002,
            preserve_topology=True
        )

        commune_features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "name": props.get("NOM_COM"),
                "commune_code": props.get("COD_COM"),
                "province_code": props.get("CODMOP_PROV"),
                "province_cine": props.get("CINE_PROV"),
                "official_id": props.get("OBJECTID"),
                "source": "MOP · Límites administrativos"
            }
        })

    # 2. Provincias
    log("Descargando límites provinciales")

    provinces = build_admin_layer(
        URL_PROVINCIA,
        "NOM_PROV",
        "provinces.geojson"
    )

    save_geojson(
        "communes.geojson",
        commune_features
    )

    # 3. Ríos, esteros y quebradas
    log("Descargando cauces DGA/SNIA")

    river_records = feature_records(
        fetch_features(
            URL_CAUCE,
            "REGION = 12"
        )
    )

    river_records = bounds_filter(river_records)

    river_features = build_water_records(
        river_records,
        "DGA/SNIA",
        "river",
        communes
    )

    # 4. Lagos y sistemas lacustres
    log("Descargando sistemas lacustres MOP")

    lake_records = feature_records(
        fetch_features(
            URL_LAGOS,
            "COD_REG = '12'"
        )
    )

    lake_records = bounds_filter(lake_records)

    lake_features = build_water_records(
        lake_records,
        "MOP/RED_HIDROGRAFICA",
        "lake",
        communes
    )

    all_waters = river_features + lake_features

    all_waters.sort(
        key=lambda item: (
            item["properties"]["name"].lower(),
            item["properties"]["water_type"]
        )
    )

    # 5. Archivos finales
    save_geojson(
        "waterbodies.geojson",
        all_waters
    )

    metadata = {
        "application": "AnglerMap",
        "region": "Magallanes y de la Antártica Chilena",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "sources": [
            {
                "name": "DGA / SNIA · Cauces de Chile",
                "url": URL_CAUCE,
                "use": "Ríos, esteros y quebradas",
                "filter": "REGION = 12"
            },
            {
                "name": "MOP · Red Hidrográfica",
                "url": URL_LAGOS,
                "use": "Lagos, lagunas y sistemas lacustres",
                "filter": "COD_REG = '12'"
            },
            {
                "name": "MOP · Límites administrativos",
                "url": URL_COMUNA,
                "use": "Geometrías comunales"
            },
            {
                "name": "MOP · Límites administrativos",
                "url": URL_PROVINCIA,
                "use": "Geometrías provinciales"
            }
        ],
        "counts": {
            "communes": len(commune_features),
            "provinces": len(provinces),
            "rivers_and_streams": len(river_features),
            "lakes_and_lagoons": len(lake_features),
            "waterbodies": len(all_waters)
        },
        "limitations": [
            "La cobertura depende de las capas oficiales consultadas.",
            "La comuna Antártica requiere una consulta geográfica específica y no se considera cubierta por el recorte continental actual.",
            "La geometría oficial no acredita acceso público ni permiso de pesca.",
            "Los cauces sin nombre se mantienen identificados por su ID oficial.",
            "La agrupación de tramos por nombre y cuenca requiere validación cartográfica."
        ]
    }

    metadata_path = META / "sources.json"

    with metadata_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2
        )

    log("Construcción finalizada correctamente")
    log(
        json.dumps(
            metadata["counts"],
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log("ERROR: " + str(error))
        raise
