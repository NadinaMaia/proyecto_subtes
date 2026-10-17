"""Genera la capa geográfica canónica usada por el dashboard.

Fuente: Buenos Aires Data, dataset oficial "Subte: Estaciones".
Se conserva una sola coordenada por estación de la red y se traducen los
nombres extendidos publicados por la Ciudad al diccionario canónico del TP.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path("/private/tmp/estaciones_de_subte.geojson")
OUTPUT = ROOT / "subte_fpca_work" / "insumos" / "estaciones_georreferenciadas.csv"
SOURCE_URL = (
    "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/sbase/"
    "subte-estaciones/estaciones_de_subte.geojson"
)


def norm(value: str) -> str:
    value = "".join(
        c for c in unicodedata.normalize("NFKD", str(value))
        if not unicodedata.combining(c)
    ).upper()
    return re.sub(r"[^A-Z0-9]+", " ", value).strip()


# El GeoJSON vigente usa denominaciones extendidas; el valor es la identidad
# histórica que ya emplea station_slot_cal en el notebook.
ALIASES_OFICIALES = {
    ("A", "CONGRESO PDTE DR RAUL ALFONSIN"): "CONGRESO",
    ("A", "PLAZA DE MISERERE"): "PLAZA MISERERE",
    ("A", "SAN JOSE DE FLORES"): "FLORES",
    ("A", "SAENZ PENA"): "SAENZ PEÑA",
    ("B", "C PELLEGRINI"): "CARLOS PELLEGRINI",
    ("B", "CALLAO MAESTRO ALFREDO BRAVO"): "CALLAO",
    ("B", "PASTEUR AMIA"): "PASTEUR",
    ("B", "ALMAGRO MEDRANO"): "MEDRANO",
    ("B", "LEANDRO N ALEM"): "LEANDRO N. ALEM",
    ("B", "MALABIA OSVALDO PUGLIESE"): "MALABIA",
    ("B", "TRONADOR VILLA ORTUZAR"): "TRONADOR",
    ("B", "DE LOS INCAS PQUE CHAS"): "LOS INCAS",
    ("B", "ECHEVERRIA MARTIRES PALOTINOS"): "ECHEVERRIA",
    ("B", "JUAN MANUEL DE ROSAS VILLA URQUIZA"): "ROSAS",
    ("C", "AV DE MAYO"): "AVENIDA DE MAYO",
    ("C", "MORENO"): "MARIANO MORENO",
    ("C", "SAN MARTIN"): "GENERAL SAN MARTIN",
    ("D", "AGUERO"): "AGÜERO",
    ("D", "TRIBUNALES TEATRO COLON"): "TRIBUNALES",
    ("D", "R SCALABRINI ORTIZ"): "SCALABRINI ORTIZ",
    ("D", "MINISTRO CARRANZA MIGUEL ABUELO"): "MINISTRO CARRANZA",
    ("E", "BELGRANO"): "GENERAL BELGRANO",
    ("E", "INDEPENDENCIA BEATA MAMA ANTULA"): "INDEPENDENCIA",
    ("E", "ENTRE RIOS RODOLFO WALSH"): "ENTRE RIOS",
    ("E", "AV LA PLATA"): "AVENIDA LA PLATA",
    ("E", "PLAZA DE LOS VIRREYES EVA PERON"): "PZA. DE LOS VIRREYES",
    ("H", "INCLAN MEZQUITA AL AHMAD"): "INCLAN",
    ("H", "HUMBERTO 1"): "HUMBERTO I",
    ("H", "ONCE 30 DE DICIEMBRE"): "ONCE",
    ("H", "PARQUE PATRICIOS"): "PATRICIOS",
    ("H", "HOSPITALES RINGO BONAVENA"): "HOSPITALES",
    ("H", "SANTA FE CARLOS JAUREGUI"): "SANTA FE",
    ("H", "FACULTAD DE DERECHO JULIETA LANTERI"): "FACULTAD DE DERECHO",
}


def canonical_name(linea: str, nombre_oficial: str) -> str:
    return ALIASES_OFICIALES.get((linea, norm(nombre_oficial)), norm(nombre_oficial))


def build(input_path: Path) -> pd.DataFrame:
    geojson = json.loads(input_path.read_text(encoding="utf-8-sig"))
    rows = []
    for feature in geojson["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        linea = str(props["linea"]).strip().upper()
        estacion = canonical_name(linea, props["estacion"])
        rows.append({
            "linea": linea,
            "estacion": estacion,
            "estacion_id": f"{linea} | {estacion}",
            "latitud": float(lat),
            "longitud": float(lon),
            "nombre_oficial": props["estacion"],
            "id_oficial": props.get("id"),
            "fuente": "Buenos Aires Data — Subte: Estaciones",
            "url_fuente": SOURCE_URL,
            "fecha_descarga": date.today().isoformat(),
        })

    out = pd.DataFrame(rows).sort_values(["linea", "estacion"]).reset_index(drop=True)
    if len(out) != 90 or out["estacion_id"].duplicated().any():
        raise RuntimeError(
            "La capa oficial debe contener exactamente 90 estaciones únicas; "
            f"se obtuvieron {len(out)} filas y "
            f"{out['estacion_id'].duplicated().sum()} duplicados."
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    result = build(args.input)
    print(f"Capa geográfica creada: {OUTPUT} ({len(result)} estaciones)")
