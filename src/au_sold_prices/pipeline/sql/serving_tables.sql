-- Serving schema for Postgres. {schema} is replaced (e.g. serving_next, then swapped to serving).

CREATE SCHEMA {schema};

CREATE TABLE {schema}.property (
  property_key text PRIMARY KEY,
  address_display text NOT NULL,
  unit_number text,
  house_number text,
  street_name text,
  suburb text NOT NULL,
  postcode text,
  state text NOT NULL,
  property_type text NOT NULL,
  land_area_m2 double precision,
  zoning text,
  sale_count integer NOT NULL,
  first_sale_date date NOT NULL,
  last_sale_date date NOT NULL,
  last_sale_price bigint NOT NULL,
  cagr_pct double precision,
  holding_years double precision,
  vs_suburb_median_pct double precision,
  search_text text NOT NULL
);

CREATE TABLE {schema}.sale (
  property_key text NOT NULL,
  suburb text NOT NULL,
  state text NOT NULL,
  postcode text,
  property_type text NOT NULL,
  address_display text NOT NULL,
  land_area_m2 double precision,
  sale_date date NOT NULL,
  settlement_date date,
  price bigint NOT NULL,
  is_stat_sale boolean NOT NULL,
  is_multi_parcel boolean NOT NULL,
  prev_price bigint,
  change_pct double precision,
  years_held double precision
);

CREATE TABLE {schema}.suburb_month (
  suburb text NOT NULL,
  state text NOT NULL,
  property_type text NOT NULL,
  month date NOT NULL,
  median_price double precision NOT NULL,
  sales_count integer NOT NULL
);

CREATE TABLE {schema}.suburb_stats (
  suburb text NOT NULL,
  state text NOT NULL,
  property_type text NOT NULL,
  median_12m double precision,
  p25_12m double precision,
  p75_12m double precision,
  sales_12m integer NOT NULL,
  change_1y_pct double precision,
  change_3y_pct double precision,
  change_5y_pct double precision,
  PRIMARY KEY (suburb, state, property_type)
);

CREATE TABLE {schema}.meta (
  data_as_of date NOT NULL,
  source_version text,
  silver_rows bigint,
  rejected_rows bigint,
  built_at timestamptz
);
