-- Silver: typed, cleaned, deduplicated NSW sales. Portable between DuckDB (local) and
-- Spark SQL (Databricks). Placeholders: {bronze} {silver} are schema names.

CREATE SCHEMA IF NOT EXISTS {silver};

CREATE OR REPLACE TABLE {silver}.sales_typed AS
SELECT
  trim(district_code) AS district_code,
  trim(property_id) AS property_id,
  concat_ws('-', trim(district_code), trim(property_id)) AS property_key,
  NULLIF(trim(property_unit_number), '') AS unit_number,
  NULLIF(trim(property_house_number), '') AS house_number,
  NULLIF(trim(property_street_name), '') AS street_name,
  NULLIF(trim(property_locality), '') AS suburb,
  NULLIF(trim(property_post_code), '') AS postcode,
  'NSW' AS state,
  TRY_CAST(NULLIF(trim(area_m2), '') AS DOUBLE) AS land_area_m2,
  NULLIF(trim(zoning), '') AS zoning,
  upper(trim(nature_of_property)) AS nature_code,
  NULLIF(trim(strata_lot_number), '') AS strata_lot,
  NULLIF(trim(dealing_number), '') AS dealing_number,
  NULLIF(trim(property_legal_description), '') AS legal_description,
  TRY_CAST(NULLIF(trim(contract_date), '') AS DATE) AS contract_date,
  TRY_CAST(NULLIF(trim(settlement_date), '') AS DATE) AS settlement_date,
  CAST(TRY_CAST(NULLIF(trim(purchase_price), '') AS DOUBLE) AS BIGINT) AS price,
  CAST(TRY_CAST(NULLIF(trim(parcels_in_sale), '') AS DOUBLE) AS INT) AS parcels_in_sale,
  lower(trim(part_interest_flag)) = 'true' AS is_part_interest,
  lower(trim(non_market_price_flag)) = 'true' AS is_non_market,
  lower(trim(date_error_flag)) = 'true' AS is_date_error,
  _source_version AS source_version
FROM {bronze}.nsw_psi_raw
-- Each source file is a full snapshot, so only the newest one is used.
WHERE _source_version = (SELECT max(_source_version) FROM {bronze}.nsw_psi_raw);

CREATE OR REPLACE TABLE {silver}.sales_rejected AS
SELECT *,
  CASE
    WHEN suburb IS NULL THEN 'missing_suburb'
    WHEN price IS NULL OR price <= 0 THEN 'invalid_price'
    ELSE 'missing_date'
  END AS reject_reason
FROM {silver}.sales_typed
WHERE suburb IS NULL
   OR price IS NULL OR price <= 0
   OR coalesce(contract_date, settlement_date) IS NULL;

CREATE OR REPLACE TABLE {silver}.sales AS
WITH valid AS (
  SELECT *, coalesce(contract_date, settlement_date) AS sale_date
  FROM {silver}.sales_typed
  WHERE suburb IS NOT NULL
    AND price IS NOT NULL AND price > 0
    AND coalesce(contract_date, settlement_date) IS NOT NULL
),
ranked AS (
  SELECT *,
    row_number() OVER (
      PARTITION BY property_key, coalesce(dealing_number, ''), coalesce(legal_description, ''),
                   sale_date, price
      ORDER BY source_version DESC
    ) AS rn
  FROM valid
)
SELECT
  property_key, district_code, property_id,
  CASE
    WHEN unit_number IS NOT NULL AND house_number IS NOT NULL
      THEN concat_ws(' ', concat_ws('/', unit_number, house_number), street_name)
    ELSE concat_ws(' ', coalesce(unit_number, house_number), street_name)
  END AS address_display,
  unit_number, house_number, street_name, suburb, postcode, state,
  land_area_m2, zoning, nature_code, strata_lot, dealing_number, legal_description,
  CASE
    WHEN nature_code = 'R' AND strata_lot IS NOT NULL THEN 'unit'
    WHEN nature_code = 'R' THEN 'house'
    WHEN nature_code = 'V' THEN 'vacant land'
    ELSE 'other'
  END AS property_type,
  contract_date, settlement_date, sale_date, price,
  coalesce(parcels_in_sale, 1) AS parcels_in_sale,
  is_part_interest, is_non_market, is_date_error,
  coalesce(parcels_in_sale, 1) > 1 AS is_multi_parcel,
  (NOT is_part_interest AND NOT is_non_market AND NOT is_date_error AND price >= 10000)
    AS is_arms_length,
  (NOT is_part_interest AND NOT is_non_market AND NOT is_date_error AND price >= 10000
    AND coalesce(parcels_in_sale, 1) <= 1) AS is_stat_sale,
  source_version
FROM ranked
WHERE rn = 1;
