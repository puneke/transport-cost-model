from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .cost_model import (
    DEFAULT_DIESEL_PRICE_PER_LITRE,
    DEFAULT_FUEL_CONSUMPTION_PER_100KM,
    build_cost_model_table,
    export_cost_model,
    export_by_depot,
)
from .distances import (
    add_manual_review_marker,
    add_network_distances,
    add_validation,
    join_depots,
)
from .geocode import geocode_dataframe


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def command_geocode(args: argparse.Namespace) -> None:
    source = read_table(args.input)
    geocoded = geocode_dataframe(source, delay_seconds=args.delay)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    geocoded.to_csv(args.output, index=False)
    print(f"Wrote {len(geocoded)} geocoded rows to {args.output}")


def command_distances(args: argparse.Namespace) -> None:
    geocoded = read_table(args.geocoded)
    depots = read_table(args.depots)
    enriched = join_depots(geocoded, depots)
    enriched = add_validation(enriched)
    enriched = add_network_distances(enriched, args.graph, include_ferry=not args.no_ferry)
    enriched = add_manual_review_marker(enriched)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(args.output, index=False)
    print(f"Wrote {len(enriched)} distance rows to {args.output}")


def command_cost_model(args: argparse.Namespace) -> None:
    distances = read_table(args.distances)
    cost_model = build_cost_model_table(
        distances,
        diesel_price_per_litre=args.diesel_price_per_litre,
        fuel_consumption_per_100km=args.fuel_consumption_per_100km,
    )
    if args.split_by_depot:
        written = export_by_depot(cost_model, args.output_dir, file_format=args.format)
        print(f"Wrote {len(written)} depot files to {args.output_dir}")
    else:
        written = export_cost_model(cost_model, args.output, file_format=args.format)
        print(f"Wrote {len(cost_model)} cost-model rows to {written}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transport cost-model pipeline")
    subparsers = parser.add_subparsers(required=True)

    geocode = subparsers.add_parser("geocode", help="Geocode suburb/postcode records with Mapbox")
    geocode.add_argument("--input", required=True)
    geocode.add_argument("--output", required=True)
    geocode.add_argument("--delay", type=float, default=0.0)
    geocode.set_defaults(func=command_geocode)

    distances = subparsers.add_parser("distances", help="Join depots and calculate distances")
    distances.add_argument("--geocoded", required=True)
    distances.add_argument("--depots", required=True)
    distances.add_argument("--output", required=True)
    distances.add_argument("--graph", required=True, help="OSMnx GraphML road-network file")
    distances.add_argument(
        "--no-ferry",
        action="store_true",
        help="Do not add the Wellington-Picton ferry link used in the notebooks",
    )
    distances.set_defaults(func=command_distances)

    cost_model = subparsers.add_parser("cost-model", help="Build depot cost-model files")
    cost_model.add_argument("--distances", required=True)
    cost_model.add_argument("--output", default="data/output/cost_model.csv")
    cost_model.add_argument("--output-dir", default="data/output/cost-model-by-depot")
    cost_model.add_argument(
        "--split-by-depot",
        action="store_true",
        help="Write one file per depot instead of one notebook-style output file",
    )
    cost_model.add_argument("--format", choices=["csv", "xlsx"], default="csv")
    cost_model.add_argument(
        "--diesel-price-per-litre",
        type=float,
        default=DEFAULT_DIESEL_PRICE_PER_LITRE,
    )
    cost_model.add_argument(
        "--fuel-consumption-per-100km",
        type=float,
        default=DEFAULT_FUEL_CONSUMPTION_PER_100KM,
    )
    cost_model.set_defaults(func=command_cost_model)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
