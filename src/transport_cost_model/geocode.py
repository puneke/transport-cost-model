from __future__ import annotations

import os
import time
import unicodedata
from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests


MAPBOX_FORWARD_URL = "https://api.mapbox.com/search/geocode/v6/forward"

GEOCODE_COLUMNS = [
    "Suburb",
    "Post Code (text)",
    "Delivery Depot",
    "Charge Zone",
    "Distance (Kms)",
    "Distance (Google)",
]


@dataclass(frozen=True)
class GeocodeResult:
    longitude: float | None
    latitude: float | None
    feature_name: str | None
    feature_type: str | None


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).lower().strip()
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def standardize_postcode(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(4) if text.isdigit() else text


def promote_embedded_header(df: pd.DataFrame) -> pd.DataFrame:
    """Handle Fliway exports where the real header is the first data row."""
    if {"Suburb", "Post Code (text)"}.issubset(df.columns):
        return df

    if df.empty:
        return df

    first_row_values = {str(value).strip() for value in df.iloc[0].dropna().tolist()}
    if {"Suburb", "Post Code (text)"}.issubset(first_row_values):
        output = df.copy()
        output.columns = output.iloc[0]
        return output.iloc[1:].reset_index(drop=True)

    return df


def remove_iata_suburb_rows(df: pd.DataFrame, iata_codes: Iterable[str]) -> pd.DataFrame:
    iata = {str(code).strip().lower() for code in iata_codes if str(code).strip()}

    def keep_suburb(value: object) -> bool:
        words = str(value).lower().split()
        return not any(word in iata for word in words)

    return df[df["Suburb"].apply(keep_suburb)].copy()


def clean_fliway_source(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the raw Fliway schedule into the notebook geocoding input."""
    output = promote_embedded_header(df)
    iata_codes = (
        output["Charge Location IATA Code"].value_counts().index.tolist()
        if "Charge Location IATA Code" in output.columns
        else []
    )

    available_columns = [column for column in GEOCODE_COLUMNS if column in output.columns]
    if {"Suburb", "Post Code (text)", "Delivery Depot"}.issubset(available_columns):
        output = output[available_columns].drop_duplicates().copy()
    else:
        output = output.copy()

    if "Distance (Kms)" in output.columns:
        output = output.rename(columns={"Distance (Kms)": "Distance (Google)"})

    if iata_codes and "Suburb" in output.columns:
        output = remove_iata_suburb_rows(output, iata_codes)

    if "Suburb" in output.columns:
        output.loc[
            output["Suburb"] == "Arthur s Pass National Park",
            "Suburb",
        ] = "Arthur's Pass National Park"

    return output.dropna(subset=["Suburb", "Post Code (text)"]).reset_index(drop=True)


def prepare_suburbs(df: pd.DataFrame, iata_codes: Iterable[str] | None = None) -> pd.DataFrame:
    output = df.copy()
    output["Post Code (text)"] = output["Post Code (text)"].apply(standardize_postcode)

    if iata_codes:
        output = remove_iata_suburb_rows(output, iata_codes)

    return output.drop_duplicates()


def geocode_suburb_postcode(
    suburb: str,
    postcode: str,
    access_token: str | None = None,
    country: str = "New Zealand",
    timeout: int = 30,
) -> GeocodeResult:
    token = access_token or os.getenv("MAPBOX_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("MAPBOX_ACCESS_TOKEN is required for geocoding")

    params = {
        "locality": suburb,
        "postcode": postcode,
        "country": country,
        "access_token": token,
    }
    response = requests.get(MAPBOX_FORWARD_URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    features = data.get("features") or []
    if not features:
        return GeocodeResult(None, None, None, None)

    feature = features[0]
    coords = feature.get("geometry", {}).get("coordinates", [None, None])
    properties = feature.get("properties", {})
    return GeocodeResult(
        longitude=coords[0],
        latitude=coords[1],
        feature_name=properties.get("name"),
        feature_type=properties.get("feature_type"),
    )


def validate_geocode(row: pd.Series) -> bool:
    feature_name = normalize_text(row.get("Feature_Name") or row.get("Feature_Name (mapbox)"))
    feature_type = normalize_text(row.get("Feature_Type") or row.get("Feature_Type (mapbox)"))
    suburb = normalize_text(row.get("Suburb"))
    place = normalize_text(row.get("Place"))
    postcode = standardize_postcode(row.get("Post Code (text)"))

    if not feature_name:
        return False
    if feature_type == "postcode":
        return feature_name == postcode or feature_name in postcode
    return (
        feature_name == place
        or feature_name == suburb
        or feature_name in place
        or place in feature_name
        or feature_name in suburb
        or suburb in feature_name
    )


def geocode_dataframe(
    df: pd.DataFrame,
    access_token: str | None = None,
    delay_seconds: float = 0.0,
) -> pd.DataFrame:
    output = prepare_suburbs(clean_fliway_source(df))
    results: list[GeocodeResult] = []

    for _, row in output.iterrows():
        result = geocode_suburb_postcode(
            suburb=str(row["Suburb"]),
            postcode=str(row["Post Code (text)"]),
            access_token=access_token,
        )
        results.append(result)
        if delay_seconds:
            time.sleep(delay_seconds)

    output["Longitude (mapbox)"] = [result.longitude for result in results]
    output["Latitude (mapbox)"] = [result.latitude for result in results]
    output["Feature_Name"] = [result.feature_name for result in results]
    output["Feature_Type"] = [result.feature_type for result in results]
    output["Feature_Name (mapbox)"] = output["Feature_Name"]
    output["Feature_Type (mapbox)"] = output["Feature_Type"]
    output["Validate"] = output.apply(validate_geocode, axis=1)
    return output
