from __future__ import annotations

from pathlib import Path

import pandas as pd

from .geocode import standardize_postcode


DEFAULT_DIESEL_PRICE_PER_LITRE = 1.78
DEFAULT_FUEL_CONSUMPTION_PER_100KM = 20.0

def cost_per_km(
    diesel_price_per_litre: float = DEFAULT_DIESEL_PRICE_PER_LITRE,
    fuel_consumption_per_100km: float = DEFAULT_FUEL_CONSUMPTION_PER_100KM,
) -> float:
    return diesel_price_per_litre * (fuel_consumption_per_100km / 100)


def add_distance_cost(
    distances: pd.DataFrame,
    diesel_price_per_litre: float = DEFAULT_DIESEL_PRICE_PER_LITRE,
    fuel_consumption_per_100km: float = DEFAULT_FUEL_CONSUMPTION_PER_100KM,
) -> pd.DataFrame:
    """Mirror notebook 03: add Cost from Distance (mapbox) and keep all columns."""
    if "Distance (mapbox)" not in distances.columns:
        raise ValueError("Missing required column: Distance (mapbox)")

    output = distances.copy()
    if "Post Code (text)" in output.columns:
        output["Post Code (text)"] = output["Post Code (text)"].apply(standardize_postcode)
    output["Cost"] = (
        output["Distance (mapbox)"].astype(float)
        * cost_per_km(diesel_price_per_litre, fuel_consumption_per_100km)
    ).round(2)
    return output


def build_cost_model_table(
    distances: pd.DataFrame,
    diesel_price_per_litre: float = DEFAULT_DIESEL_PRICE_PER_LITRE,
    fuel_consumption_per_100km: float = DEFAULT_FUEL_CONSUMPTION_PER_100KM,
) -> pd.DataFrame:
    return add_distance_cost(
        distances,
        diesel_price_per_litre=diesel_price_per_litre,
        fuel_consumption_per_100km=fuel_consumption_per_100km,
    )


def export_by_depot(cost_model: pd.DataFrame, output_dir: str | Path, file_format: str = "xlsx") -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    depot_column = "Delivery Depot" if "Delivery Depot" in cost_model.columns else "depot"
    if depot_column not in cost_model.columns:
        raise ValueError("Missing required depot column: Delivery Depot or depot")

    for depot, depot_df in cost_model.groupby(depot_column, sort=True):
        safe_depot = str(depot).replace(" ", "_")
        if file_format == "xlsx":
            path = output_path / f"{safe_depot}_Cost_Model.xlsx"
            depot_df.to_excel(path, index=False)
        elif file_format == "csv":
            path = output_path / f"{safe_depot}_cost_model.csv"
            depot_df.to_csv(path, index=False)
        else:
            raise ValueError("file_format must be 'csv' or 'xlsx'")
        written.append(path)

    return written


def export_cost_model(cost_model: pd.DataFrame, output: str | Path, file_format: str | None = None) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_format = file_format or output_path.suffix.lower().lstrip(".")
    if not output_format:
        output_format = "csv"
        output_path = output_path.with_suffix(".csv")

    if output_format == "xlsx":
        if output_path.suffix.lower() != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")
        cost_model.to_excel(output_path, index=False)
    elif output_format == "csv":
        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(".csv")
        cost_model.to_csv(output_path, index=False)
    else:
        raise ValueError("file_format must be 'csv' or 'xlsx'")

    return output_path
