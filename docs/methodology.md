# Methodology

## Objective

The model estimates transport-cost inputs by converting delivery-zone records into geocoded depot-distance tables and then calculating a fuel-cost estimate from each Mapbox road distance.

## Pipeline

1. **Source preparation**
   - Start with suburb, postcode, depot, charge zone, and any existing benchmark distance.
   - Standardize postcodes as four-character strings.
   - Remove rows that are depot/IATA-code placeholders rather than real delivery locations.

2. **Geocoding**
   - Query Mapbox using structured New Zealand locality/postcode fields.
   - Store longitude, latitude, feature name, and feature type.
   - Validate results by comparing the returned feature name against the requested suburb/postcode.

3. **Depot join**
   - Join each delivery row to its depot longitude/latitude.
   - Normalize depot names before matching.

4. **Distance calculation**
   - Load an OSMnx road graph and calculate shortest-path distance between nearest road-network nodes.
   - Flag rows for manual review when geocoding failed, validation failed, manual input was requested, or no distance was calculated.

5. **Cost-model output**
   - Preserve the distance-enriched table produced by the distance step.
   - Calculate `Cost` as `Distance (mapbox) * diesel_price_per_litre * fuel_consumption_per_100km / 100`.
   - Use the notebook defaults of diesel price `1.78` per litre and fuel consumption `20` L/100km unless overridden.
   - Export one workbook matching the notebook output. Split-by-depot export is available as an optional convenience.

## Public-Repo Data Policy

The original notebooks included private operational spreadsheets, API caches, and executed outputs. A public repository should include only sample or anonymized data. Keep raw spreadsheets, generated workbooks, API caches, and road graph files outside Git.
