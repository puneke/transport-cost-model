from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd

from .geocode import normalize_text, standardize_postcode, validate_geocode


NORTH_FERRY_TERMINAL_ID = 999000001
SOUTH_FERRY_TERMINAL_ID = 999000002
FERRY_DISTANCE_METERS = 53_000


def add_ferry_connection(graph: nx.Graph) -> nx.Graph:
    """Add the notebook's Wellington-Picton ferry link to the road graph."""
    graph.add_node(
        NORTH_FERRY_TERMINAL_ID,
        x=174.7835723336724,
        y=-41.27874222366664,
    )
    graph.add_node(SOUTH_FERRY_TERMINAL_ID, x=174.00497, y=-41.28402)
    graph.add_edge(
        NORTH_FERRY_TERMINAL_ID,
        SOUTH_FERRY_TERMINAL_ID,
        length=FERRY_DISTANCE_METERS,
        ferry=True,
    )
    graph.add_edge(
        SOUTH_FERRY_TERMINAL_ID,
        NORTH_FERRY_TERMINAL_ID,
        length=FERRY_DISTANCE_METERS,
        ferry=True,
    )
    return graph


def join_depots(addresses: pd.DataFrame, depots: pd.DataFrame) -> pd.DataFrame:
    output = addresses.copy()
    output["Post Code (text)"] = output["Post Code (text)"].apply(standardize_postcode)

    depot_lookup = depots.copy()
    depot_lookup["_depot_key"] = depot_lookup["depot"].map(normalize_text)
    lat_map = depot_lookup.set_index("_depot_key")["lat"].to_dict()
    lng_map = depot_lookup.set_index("_depot_key")["lng"].to_dict()

    depot_key = output["Delivery Depot"].map(normalize_text)
    output["Longitude (depots)"] = depot_key.map(lng_map)
    output["Latitude (depots)"] = depot_key.map(lat_map)
    return output


def add_validation(addresses: pd.DataFrame) -> pd.DataFrame:
    output = addresses.copy()
    output["Validate"] = output.apply(validate_geocode, axis=1)
    return output


def add_network_distances(
    addresses: pd.DataFrame,
    graph_path: str | Path,
    include_ferry: bool = True,
) -> pd.DataFrame:
    try:
        import osmnx as ox
    except ImportError as exc:
        raise RuntimeError("Install osmnx to calculate road-network distances") from exc

    graph = ox.load_graphml(graph_path)
    if include_ferry:
        graph = add_ferry_connection(graph)
    output = addresses.copy().dropna(
        subset=[
            "Longitude (depots)",
            "Latitude (depots)",
            "Longitude (mapbox)",
            "Latitude (mapbox)",
        ]
    )

    output["Orig_Node"] = ox.distance.nearest_nodes(
        graph,
        X=output["Longitude (depots)"].astype(float).values,
        Y=output["Latitude (depots)"].astype(float).values,
    )
    output["Dest_Node"] = ox.distance.nearest_nodes(
        graph,
        X=output["Longitude (mapbox)"].astype(float).values,
        Y=output["Latitude (mapbox)"].astype(float).values,
    )

    def distance(row: pd.Series) -> float | None:
        try:
            meters = nx.shortest_path_length(
                graph,
                row["Orig_Node"],
                row["Dest_Node"],
                weight="length",
            )
            return round(meters / 1000, 2)
        except nx.NetworkXNoPath:
            return None

    output["Distance (mapbox)"] = output.apply(distance, axis=1)
    return output


def add_manual_review_marker(addresses: pd.DataFrame) -> pd.DataFrame:
    output = addresses.copy()

    def marker(row: pd.Series) -> bool:
        manual_input = normalize_text(row.get("Manual_Input"))
        validate = row.get("Validate")
        return (
            manual_input == "y"
            or validate is False
            or validate == False
            or pd.isna(row.get("Distance (mapbox)"))
        )

    output["Final Marker"] = output.apply(marker, axis=1)
    return output
