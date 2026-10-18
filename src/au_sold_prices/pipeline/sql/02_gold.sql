-- Gold: serving-ready tables built from silver. Portable between DuckDB and Spark SQL.
-- Placeholders: {silver} {gold} schema names; {as_of} and {as_of_1y}..{as_of_6y} ISO dates
-- (the newest sale date and that date minus N years). @days(a, b) means whole days from a to b.

CREATE SCHEMA IF NOT EXISTS {gold};

CREATE OR REPLACE TABLE {gold}.sale AS
WITH base AS (
  SELECT *,
    lag(price) OVER (PARTITION BY property_key ORDER BY sale_date, coalesce(dealing_number, ''))
      AS prev_price,
    lag(sale_date) OVER (PARTITION BY property_key ORDER BY sale_date, coalesce(dealing_number, ''))
      AS prev_date
  FROM {silver}.sales
  WHERE is_arms_length
)
SELECT
  property_key, suburb, state, postcode, property_type, address_display, land_area_m2,
  sale_date, settlement_date, price, is_stat_sale, is_multi_parcel, prev_price,
  CASE WHEN prev_price > 0 THEN (price * 1.0 / prev_price - 1) * 100 END AS change_pct,
  CASE WHEN prev_date IS NOT NULL THEN @days(prev_date, sale_date) / 365.25 END AS years_held
FROM base;

CREATE OR REPLACE TABLE {gold}.suburb_month AS
SELECT
  suburb, state, property_type,
  CAST(date_trunc('month', sale_date) AS DATE) AS month,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  count(*) AS sales_count
FROM {gold}.sale
WHERE is_stat_sale
GROUP BY suburb, state, property_type, CAST(date_trunc('month', sale_date) AS DATE);

CREATE OR REPLACE TABLE {gold}.suburb_stats AS
WITH cur AS (
  SELECT suburb, state, property_type,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_12m,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY price) AS p25_12m,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY price) AS p75_12m,
    count(*) AS sales_12m
  FROM {gold}.sale
  WHERE is_stat_sale AND sale_date > DATE '{as_of_1y}' AND sale_date <= DATE '{as_of}'
  GROUP BY suburb, state, property_type
),
p1 AS (
  SELECT suburb, state, property_type,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price
  FROM {gold}.sale
  WHERE is_stat_sale AND sale_date > DATE '{as_of_2y}' AND sale_date <= DATE '{as_of_1y}'
  GROUP BY suburb, state, property_type
),
p3 AS (
  SELECT suburb, state, property_type,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price
  FROM {gold}.sale
  WHERE is_stat_sale AND sale_date > DATE '{as_of_4y}' AND sale_date <= DATE '{as_of_3y}'
  GROUP BY suburb, state, property_type
),
p5 AS (
  SELECT suburb, state, property_type,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price
  FROM {gold}.sale
  WHERE is_stat_sale AND sale_date > DATE '{as_of_6y}' AND sale_date <= DATE '{as_of_5y}'
  GROUP BY suburb, state, property_type
)
SELECT
  cur.suburb, cur.state, cur.property_type,
  cur.median_12m, cur.p25_12m, cur.p75_12m, cur.sales_12m,
  (cur.median_12m / p1.median_price - 1) * 100 AS change_1y_pct,
  (cur.median_12m / p3.median_price - 1) * 100 AS change_3y_pct,
  (cur.median_12m / p5.median_price - 1) * 100 AS change_5y_pct
FROM cur
LEFT JOIN p1 USING (suburb, state, property_type)
LEFT JOIN p3 USING (suburb, state, property_type)
LEFT JOIN p5 USING (suburb, state, property_type);

CREATE OR REPLACE TABLE {gold}.property AS
WITH ranked AS (
  SELECT s.*,
    row_number() OVER (PARTITION BY property_key
                       ORDER BY sale_date DESC, coalesce(dealing_number, '') DESC) AS rn_last,
    row_number() OVER (PARTITION BY property_key
                       ORDER BY sale_date ASC, coalesce(dealing_number, '') ASC) AS rn_first,
    count(*) OVER (PARTITION BY property_key) AS sale_count,
    max(land_area_m2) OVER (PARTITION BY property_key) AS best_land_area_m2
  FROM {silver}.sales s
  WHERE is_arms_length
),
last_sale AS (SELECT * FROM ranked WHERE rn_last = 1),
first_sale AS (SELECT property_key, sale_date AS first_date, price AS first_price
               FROM ranked WHERE rn_first = 1)
SELECT
  l.property_key, l.address_display, l.unit_number, l.house_number, l.street_name,
  l.suburb, l.postcode, l.state, l.property_type,
  l.best_land_area_m2 AS land_area_m2, l.zoning, l.sale_count,
  f.first_date AS first_sale_date,
  l.sale_date AS last_sale_date, l.price AS last_sale_price,
  CASE
    WHEN l.sale_count >= 2 AND @days(f.first_date, l.sale_date) >= 365 AND f.first_price > 0
      THEN (power(l.price * 1.0 / f.first_price, 365.25 / @days(f.first_date, l.sale_date)) - 1) * 100
  END AS cagr_pct,
  @days(l.sale_date, DATE '{as_of}') / 365.25 AS holding_years,
  CASE WHEN m.median_price > 0 THEN (l.price * 1.0 / m.median_price - 1) * 100 END
    AS vs_suburb_median_pct,
  lower(concat_ws(' ', l.address_display, l.suburb, l.postcode)) AS search_text
FROM last_sale l
JOIN first_sale f USING (property_key)
LEFT JOIN {gold}.suburb_month m
  ON m.suburb = l.suburb AND m.state = l.state AND m.property_type = l.property_type
 AND m.month = CAST(date_trunc('month', l.sale_date) AS DATE);

CREATE OR REPLACE TABLE {gold}.meta AS
SELECT DATE '{as_of}' AS data_as_of,
       (SELECT max(source_version) FROM {silver}.sales) AS source_version,
       (SELECT count(*) FROM {silver}.sales) AS silver_rows,
       (SELECT count(*) FROM {silver}.sales_rejected) AS rejected_rows,
       CAST(current_timestamp AS TIMESTAMP) AS built_at;
