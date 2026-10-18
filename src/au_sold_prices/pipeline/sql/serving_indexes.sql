-- Indexes created after the bulk load. Requires the pg_trgm extension.
CREATE INDEX property_prefix_idx ON {schema}.property (search_text text_pattern_ops);
CREATE INDEX property_trgm_idx ON {schema}.property USING gin (search_text gin_trgm_ops);
CREATE INDEX sale_property_idx ON {schema}.sale (property_key, sale_date DESC);
CREATE INDEX sale_comps_idx ON {schema}.sale (suburb, state, property_type, sale_date DESC) WHERE is_stat_sale;
CREATE INDEX suburb_month_idx ON {schema}.suburb_month (suburb, state, property_type, month);
