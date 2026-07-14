# Transport Cost Model

Client requied a more robust costing model. Starting with a dataset of locations, this project documents the creation of a transport cost model pipline:

1. Prepare suburb/postcode delivery zones.
2. Geocode each suburb/postcode pair.
3. Join depot coordinates.
4. Calculate depot to location road distances.
5. Add fuel cost estimates and export a final cost model table.

The original work was developed in notebooks. This repository keeps the reusable parts as Python modules and uses small sample CSV files so the workflow can be reviewed without private operational data. The CLI is the reproducible run path; the notebooks are retained as methodology and development history.

## Repository Layout

```text
src/transport_cost_model/
  geocode.py      # Mapbox geocoding and geocode validation
  distances.py    # depot joins, geocode validation, road network distances
  cost_model.py   # depot cost-model table/export generation
  cli.py          # command-line entry points
data/sample/
  suburbs.csv     # anonymized/sample delivery zone rows
  depots.csv      # sample depot coordinates
  suburbs_with_distances.csv  # sample distance enriched input for cost model demo
docs/
  methodology.md  # project method and assumptions
```

## Quick Start

Create an environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Build a sample cost-model CSV without calling external APIs:

```bash
python -m transport_cost_model.cli cost-model \
  --distances data/sample/suburbs_with_distances.csv \
  --output data/output/cost_model.csv
```

Use `--format xlsx --output data/output/cost_model.xlsx` if you want an Excel workbook instead.

The cost-model step calculates `Cost` from `Distance (mapbox)` using the notebook defaults:
diesel price `1.78` per litre and fuel consumption `20` L/100km. Override with
`--diesel-price-per-litre` and `--fuel-consumption-per-100km` if needed.

Use `--split-by-depot --output-dir data/output/cost-model-by-depot` if you want
separate depot files as an extra export convenience.

## Notebooks

The notebooks mirror the original analysis workflow:

- `01_geocode_suburbs.ipynb` prepares the raw delivery schedule and geocodes suburb/postcode pairs with Mapbox.
- `02_calculate_distances.ipynb` joins depot coordinates and calculates road-network distances.
- `03_build_cost_model.ipynb` adds the fuel-cost estimate to the distance-enriched table.

They require private raw files and, for geocoding, a Mapbox token. For review or automation, use the CLI commands above.

## Geocoding

Mapbox geocoding is optional and requires an environment variable:

```bash
export MAPBOX_ACCESS_TOKEN=...
python -m transport_cost_model.cli geocode \
  --input data/raw/fliway_source_to_geocode.xlsx \
  --output data/output/geocoded_structured.csv
```

Do not commit real API tokens, raw customer data, generated caches, or full output workbooks.

## Distance Calculation

Distance calculation requires an OSMnx compatible GraphML road network file:

```bash
python -m transport_cost_model.cli distances \
  --geocoded data/output/geocoded_structured.csv \
  --depots data/raw/depots_geocoded.xlsx \
  --graph data/raw/new_zealand.graphml \
  --output data/output/distances_mapbox_google.csv
```

By default the distance step adds the Wellington to Picton ferry link used in the notebooks.
