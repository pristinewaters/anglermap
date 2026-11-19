
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from shapely.geometry import (
    shape, mapping, LineString, MultiLineString,
    Polygon, MultiPolygon, box
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

REGION_BOUNDS = box(-76.5, -56.2, -65.5, -48.0)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AnglerMap-Geodata/1.0 (public geographic data)"
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
    value = re.sub(r"\s+", " ", value)
    return value


def arcgis_request(url, params):
    response = SESSION.get(
        url + "/query",
        params=params,
        timeout=120
    )
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(
            "ArcGIS: " + json.dumps(data["error"], ensure_ascii=False)
        )

    return data


def fetch_features(layer_url, where="1=1"):
    log("Consultando " + layer_url)

    ids_data = arcgis_request(layer_url, {
        "where": where,
        "returnIdsOnly": "true",
        "f": "json"
    })

    object_ids = ids_data.get("objectIds") or []

    if not object_ids:
        log("Sin registros para: " + where)
        return []

    log("Registros identificados: " + str(len(object_ids)))

    features = []

    for start in range(0, len(object_ids), 250):
        batch = object_ids[start:start + 250]

        data = arcgis_request(layer_url, {
            "objectIds": ",".join(map(str, batch)),
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json"
        })

        features.extend(data.get("features", []))

        log(
            "Descargados "
            + str(min(start + len(batch), len(object_ids)))
            + " de "
            + str(len(object_ids))
        )

    return features


def esri_geometry_to_shape(geometry):
    if not geometry:
        return None

    if "paths" in geometry:
        paths = geometry["paths"]

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
    result = []

    for record in records:
        if record["geometry"].intersects(REGION_BOUNDS):
            result.append(record)

    return result


def build_admin_layer(url, name_field, output):
    records = feature_records(
        fetch_features(url)
    )

    records = bounds_filter(records)

    features = []

    for record in records:
        geom = record["geometry"]
        props = record["properties"]

        geom = geom.simplify(
            0.00002,
            preserve_topology=True
        )

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

    if "estero" in value:
        return "stream"

    if "quebrada" in value:
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

        name = (
            props.get("NOMBRE")
            or props.get("NOMBRESS")
            or ""
        ).strip()

        alternate = (
            props.get("NOMBRESS")
            or props.get("NOMBRE")
            or ""
        ).strip()

        official_id = props.get("OBJECTID")

        if not name:
            name = "Cauce sin nombre"

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

        if not name or name == "Cauce sin nombre":
            group_key = group_key + (str(official_id),)

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

        if alternate and alternate != name:
            group["alternates"].add(alternate)

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
            set(str(value) for value in group["official_ids"])
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

    # Límites administrativos
    log("Descargando comunas")
    communes = feature_records(
        fetch_features(URL_COMUNA)
    )
    communes = bounds_filter(communes)

    log("Descargando provincias")
    provinces = build_admin_layer(
        URL_PROVINCIA,
        "NOM_PROV",
        "provinces.geojson"
    )

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

    save_geojson("communes.geojson", commune_features)

    # Ríos, esteros y quebradas DGA
    log("Descargando cauces DGA de la Región 12")
    river_records = feature_records(
        fetch_features(URL_CAUCE, "REGION = 12")
    )

    river_records = bounds_filter(river_records)

    river_features = build_water_records(
        river_records,
        "DGA/SNIA",
        "river",
        communes
    )

    # Lagos, lagunas y otros sistemas lacustres
    log("Descargando sistemas lacustres MOP")
    lake_records = feature_records(
        fetch_features(URL_LAGOS, "COD_REG = '12'")
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

    save_geojson("waterbodies.geojson", all_waters)

    # Metadatos de generación y procedencia
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
            "La cobertura territorial depende de las fuentes oficiales.",
            "La comuna Antártica debe verificarse por separado.",
            "La geometría oficial no acredita acceso público ni permiso de pesca.",
            "Los cauces sin nombre se mantienen identificados por su ID oficial."
        ]
    }

    with (META / "sources.json").open(
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
    log(json.dumps(metadata["counts"], ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log("ERROR: " + str(error))
        raise
