-- Canonical PostgreSQL 18 / PostGIS 3.6 catalogue schema.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA catalog;
SET search_path = catalog, public;
SET TIME ZONE 'UTC';

CREATE DOMAIN iso_timestamp AS text CHECK (
  VALUE ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$'
  AND isfinite(VALUE::timestamptz));
CREATE DOMAIN iso_date AS text CHECK (
  VALUE ~ '^\d{4}-\d{2}-\d{2}$' AND isfinite(VALUE::date));
CREATE DOMAIN nonempty_text AS text CHECK (length(btrim(VALUE)) > 0);
CREATE DOMAIN finite_float AS double precision
  CHECK (VALUE > '-Infinity'::float8 AND VALUE < 'Infinity'::float8);
CREATE DOMAIN nonnegative_float AS finite_float CHECK (VALUE >= 0);
CREATE DOMAIN object_id AS text CHECK (VALUE ~ '^[A-Z]{2,3}-[0-9]{4,}$');
CREATE DOMAIN cave_id AS text CHECK (VALUE ~ '^C-[0-9]{4,}$');
CREATE DOMAIN measurement_id AS text CHECK (VALUE ~ '^m-[0-9]{3,}$');
CREATE TYPE bibliography_state AS ENUM ('known', 'unknown');
CREATE TYPE selection_mode AS ENUM ('auto', 'manual');
CREATE TYPE category AS ENUM ('jaskinia_otwor','ponor','wywierzysko','sztolnia','inne');
CREATE TYPE measurement_source AS ENUM ('TPN','PIG','geoportal','wlasne','publikacja','inne');
CREATE TYPE measurement_method AS ENUM
  ('gps_receiver','gnss','smartfon','mapa_topo','source_record','siec_pomiarowa','ustalenie','inne');
CREATE TYPE verification_state AS ENUM ('nieweryfikowany','zweryfikowany','odrzucony');
CREATE TYPE elevation_datum AS ENUM ('unknown','ellipsoidal','PL-EVRF2007-NH','Kronstadt86','other');
CREATE TYPE elevation_source AS ENUM ('gps','gnss','map','dem','barometric','source_record','unknown','other');
CREATE TYPE reference_system AS ENUM ('TPN','PIG','geoportal','NR_INWENT','inne');
CREATE TYPE reference_kind AS ENUM ('source_globalid','inventory_number','catalog_id','url','source_row','other');
CREATE TYPE reference_scope AS ENUM ('object','cave','cave_system','inventory_entry','unknown');

CREATE TABLE caves (
  fields_present text[] NOT NULL,
  schema_version integer NOT NULL CHECK (schema_version=1),
  id cave_id PRIMARY KEY,
  name nonempty_text NOT NULL,
  system_name text,
  bibliography_status bibliography_state NOT NULL,
  bibliography_note text,
  notes text,
  created_at iso_timestamp NOT NULL,
  created_by nonempty_text NOT NULL,
  updated_at iso_timestamp NOT NULL,
  updated_by nonempty_text NOT NULL
);

CREATE TABLE objects (
  fields_present text[] NOT NULL,
  schema_version integer NOT NULL CHECK (schema_version=1),
  id object_id PRIMARY KEY,
  category category NOT NULL,
  name_local text,
  cave_id cave_id REFERENCES caves(id) DEFERRABLE INITIALLY DEFERRED,
  membership_ordinal integer CHECK (membership_ordinal > 0),
  UNIQUE(cave_id,membership_ordinal),
  CHECK ((cave_id IS NULL) = (membership_ordinal IS NULL)),
  bibliography_status bibliography_state NOT NULL,
  bibliography_note text,
  assignment_fields_present text[] NOT NULL,
  assignment_mode selection_mode NOT NULL,
  assigned_from_measurement_id measurement_id NOT NULL,
  assigned_prefix text NOT NULL CHECK (assigned_prefix ~ '^[A-Z]{2,3}$'),
  prefix_override_reason text,
  notes text,
  created_at iso_timestamp NOT NULL,
  created_by nonempty_text NOT NULL,
  updated_at iso_timestamp NOT NULL,
  updated_by nonempty_text NOT NULL,
  CHECK (assignment_mode <> 'manual' OR NULLIF(btrim(prefix_override_reason),'') IS NOT NULL),
  CHECK (split_part(id, '-', 1) = assigned_prefix)
);

CREATE TABLE measurements (
  fields_present text[] NOT NULL,
  object_id object_id NOT NULL REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  id measurement_id NOT NULL,
  history_order integer NOT NULL CHECK (history_order > 0),
  input_geom geometry(Point) NOT NULL,
  elevation_m finite_float,
  elevation_datum elevation_datum,
  elevation_source elevation_source,
  horizontal_accuracy_m nonnegative_float,
  vertical_accuracy_m nonnegative_float,
  source measurement_source NOT NULL,
  source_ref text,
  observed_at iso_timestamp,
  observed_date iso_date NOT NULL,
  source_date iso_date,
  method measurement_method NOT NULL,
  device text,
  verification_status verification_state NOT NULL,
  verified_by nonempty_text,
  verified_at iso_timestamp,
  notes text,
  created_at iso_timestamp NOT NULL,
  created_by nonempty_text NOT NULL,
  PRIMARY KEY (object_id, id),
  UNIQUE (object_id, history_order),
  CHECK (ST_SRID(input_geom) IN (4326,2180)),
  CHECK (NOT ST_IsEmpty(input_geom) AND ST_NDims(input_geom)=2),
  CHECK (ST_X(input_geom) > '-Infinity'::float8 AND ST_X(input_geom) < 'Infinity'::float8),
  CHECK (ST_Y(input_geom) > '-Infinity'::float8 AND ST_Y(input_geom) < 'Infinity'::float8),
  CHECK (ST_SRID(input_geom) <> 4326 OR
    (ST_X(input_geom) BETWEEN -180 AND 180 AND ST_Y(input_geom) BETWEEN -90 AND 90))
);
ALTER TABLE objects ADD CONSTRAINT assignment_same_object_fk
  FOREIGN KEY (id, assigned_from_measurement_id) REFERENCES measurements(object_id,id)
  DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE measurement_tags (
  object_id object_id NOT NULL,
  measurement_id measurement_id NOT NULL,
  ordinal integer NOT NULL CHECK (ordinal > 0),
  tag nonempty_text NOT NULL,
  PRIMARY KEY (object_id,measurement_id,tag),
  UNIQUE (object_id,measurement_id,ordinal),
  FOREIGN KEY (object_id,measurement_id) REFERENCES measurements(object_id,id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE best_policy (
  fields_present text[] NOT NULL,
  object_id object_id PRIMARY KEY REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  mode selection_mode NOT NULL,
  manual_measurement_id measurement_id,
  reason text,
  updated_at iso_timestamp NOT NULL,
  updated_by nonempty_text NOT NULL,
  FOREIGN KEY (object_id,manual_measurement_id) REFERENCES measurements(object_id,id) DEFERRABLE INITIALLY DEFERRED,
  CHECK ((mode='auto' AND manual_measurement_id IS NULL) OR
    (mode='manual' AND manual_measurement_id IS NOT NULL AND NULLIF(btrim(reason),'') IS NOT NULL))
);

CREATE TABLE object_external_refs (
  fields_present text[] NOT NULL,
  object_id object_id NOT NULL REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  ordinal integer NOT NULL CHECK (ordinal > 0),
  system reference_system NOT NULL,
  ref_type reference_kind NOT NULL,
  external_id nonempty_text NOT NULL,
  url text,
  scope reference_scope,
  notes text,
  PRIMARY KEY (object_id,ordinal)
);
CREATE UNIQUE INDEX unique_tpn_globalid ON object_external_refs(external_id)
  WHERE system='TPN' AND ref_type='source_globalid';
CREATE TABLE cave_external_refs (
  fields_present text[] NOT NULL,
  cave_id cave_id NOT NULL REFERENCES caves(id) DEFERRABLE INITIALLY DEFERRED,
  ordinal integer NOT NULL CHECK (ordinal > 0),
  system reference_system NOT NULL,
  ref_type reference_kind NOT NULL,
  external_id nonempty_text NOT NULL,
  url text,
  scope reference_scope,
  notes text,
  PRIMARY KEY (cave_id,ordinal)
);

CREATE TABLE publications (
  fields_present text[] NOT NULL,
  id text PRIMARY KEY CHECK (id ~ '^[a-z0-9][a-z0-9_-]*$'),
  citation nonempty_text NOT NULL,
  authors text,
  title text,
  publication_year integer CHECK (publication_year BETWEEN 1 AND 9999),
  container_title text,
  issue text,
  url text,
  doi text,
  isbn text
);
CREATE TABLE cave_citations (
  ordinal integer NOT NULL CHECK (ordinal > 0),
  fields_present text[] NOT NULL,
  cave_id cave_id NOT NULL REFERENCES caves(id) DEFERRABLE INITIALLY DEFERRED,
  publication_id text NOT NULL REFERENCES publications(id) DEFERRABLE INITIALLY DEFERRED,
  locator nonempty_text NOT NULL,
  name_in_source text,
  purpose text NOT NULL CHECK (purpose IN ('existence','identity','description')),
  notes text,
  UNIQUE(cave_id,ordinal),
  PRIMARY KEY (cave_id,publication_id,locator)
);
CREATE TABLE object_citations (
  ordinal integer NOT NULL CHECK (ordinal > 0),
  fields_present text[] NOT NULL,
  object_id object_id NOT NULL REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  publication_id text NOT NULL REFERENCES publications(id) DEFERRABLE INITIALLY DEFERRED,
  locator nonempty_text NOT NULL,
  name_in_source text,
  purpose text NOT NULL CHECK (purpose IN ('existence','identity','description')),
  notes text,
  UNIQUE(object_id,ordinal),
  PRIMARY KEY (object_id,publication_id,locator)
);
CREATE TABLE measurement_citations (
  ordinal integer NOT NULL CHECK (ordinal > 0),
  fields_present text[] NOT NULL,
  object_id object_id NOT NULL,
  measurement_id measurement_id NOT NULL,
  publication_id text NOT NULL REFERENCES publications(id) DEFERRABLE INITIALLY DEFERRED,
  locator nonempty_text NOT NULL,
  notes text,
  UNIQUE(object_id,measurement_id,ordinal),
  PRIMARY KEY (object_id,measurement_id,publication_id,locator),
  FOREIGN KEY (object_id,measurement_id) REFERENCES measurements(object_id,id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE attachments (
  ordinal integer NOT NULL CHECK (ordinal > 0),
  fields_present text[] NOT NULL,
  object_id object_id NOT NULL REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  id text NOT NULL CHECK (id ~ '^a-[0-9]{3,}$'),
  kind text NOT NULL CHECK (kind IN ('raport_gnss','zdjecie','inne')),
  measurement_id measurement_id,
  path nonempty_text NOT NULL,
  caption text,
  date iso_date,
  created_at iso_timestamp NOT NULL,
  created_by nonempty_text NOT NULL,
  UNIQUE(object_id,ordinal),
  PRIMARY KEY (object_id,id),
  FOREIGN KEY (object_id,measurement_id) REFERENCES measurements(object_id,id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE relations (
  fields_present text[] NOT NULL,
  schema_version integer NOT NULL CHECK (schema_version=1),
  id text PRIMARY KEY CHECK (id ~ '^R-[0-9]{4,}$'),
  from_object_id object_id NOT NULL REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  to_object_id object_id NOT NULL REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
  relation_type text NOT NULL CHECK (relation_type IN ('sasiad','czesc_systemu','mozliwy_duplikat','inne')),
  notes text
);

CREATE VIEW cave_members AS
SELECT cave_id, id AS object_id, membership_ordinal AS ordinal FROM objects WHERE cave_id IS NOT NULL;

CREATE VIEW v_measurements AS
SELECT m.*, ST_SRID(input_geom) AS input_srid,
  ST_X(input_geom) AS input_x, ST_Y(input_geom) AS input_y, ST_Y(g.wgs84) AS lat, ST_X(g.wgs84) AS lon,
  ST_Y(g.pl1992) AS x_1992, ST_X(g.pl1992) AS y_1992,
  g.wgs84 AS geom_wgs84, g.pl1992 AS geom_1992
FROM measurements m
CROSS JOIN LATERAL (SELECT ST_Transform(input_geom,4326) wgs84,
                           ST_Transform(input_geom,2180) pl1992) g;

CREATE VIEW v_auto_best AS
SELECT object_id,id AS measurement_id,priority,priority=5 AS rejected_fallback
FROM (
  SELECT m.*, ROW_NUMBER() OVER (PARTITION BY object_id ORDER BY priority,
    COALESCE(observed_at::timestamptz,observed_date::timestamp AT TIME ZONE 'UTC') DESC,
    horizontal_accuracy_m ASC NULLS LAST, id COLLATE "C" ASC) AS rn
  FROM (
    SELECT measurements.*, CASE
      WHEN source='wlasne' AND verification_status='zweryfikowany' THEN 0
      WHEN source='TPN' AND verification_status<>'odrzucony' THEN 1
      WHEN source='wlasne' AND verification_status<>'odrzucony' THEN 2
      WHEN source='PIG' AND verification_status<>'odrzucony' THEN 3
      WHEN verification_status<>'odrzucony' THEN 4 ELSE 5 END AS priority
    FROM measurements
  ) m
) r WHERE rn=1;

CREATE VIEW v_best AS
SELECT m.*, o.name_local,o.cave_id,o.category,
  p.mode AS best_mode,p.reason AS best_reason,
  CASE WHEN p.mode='auto' THEN a.rejected_fallback ELSE false END AS rejected_fallback
FROM objects o JOIN best_policy p ON p.object_id=o.id
JOIN v_auto_best a ON a.object_id=o.id
JOIN v_measurements m ON m.object_id=o.id AND m.id=
  CASE WHEN p.mode='manual' THEN p.manual_measurement_id ELSE a.measurement_id END;

-- These cross-row rules are CI queries, not CHECK expressions.
CREATE VIEW v_integrity_issues AS
SELECT 'OBJECT_WITHOUT_MEASUREMENT'::text code,o.id::text entity_id
FROM objects o WHERE NOT EXISTS (SELECT FROM measurements m WHERE m.object_id=o.id)
UNION ALL
SELECT 'OBJECT_WITHOUT_BEST_POLICY',o.id FROM objects o
WHERE NOT EXISTS (SELECT FROM best_policy p WHERE p.object_id=o.id)
UNION ALL
SELECT 'CAVE_BIBLIOGRAPHY_KNOWN_WITHOUT_CITATION',c.id FROM caves c
WHERE bibliography_status='known' AND NOT EXISTS (SELECT FROM cave_citations r WHERE r.cave_id=c.id)
UNION ALL
SELECT 'OBJECT_BIBLIOGRAPHY_KNOWN_WITHOUT_CITATION',o.id FROM objects o
WHERE bibliography_status='known' AND NOT EXISTS (SELECT FROM object_citations r WHERE r.object_id=o.id)
UNION ALL
SELECT 'DUPLICATE_EXTERNAL_REFERENCE',object_id FROM object_external_refs r
GROUP BY object_id,(to_jsonb(r)-'ordinal') HAVING count(*)>1
UNION ALL
SELECT 'DUPLICATE_EXTERNAL_REFERENCE',cave_id FROM cave_external_refs r
GROUP BY cave_id,(to_jsonb(r)-'ordinal') HAVING count(*)>1;

CREATE VIEW v_warnings AS
SELECT 'CAVE_BIBLIOGRAPHY_UNKNOWN'::text code,id::text entity_id,NULL::text measurement_id
FROM caves WHERE bibliography_status='unknown'
UNION ALL
SELECT 'OBJECT_BIBLIOGRAPHY_UNKNOWN',id,NULL FROM objects WHERE bibliography_status='unknown'
UNION ALL
SELECT 'MISSING_HORIZONTAL_ACCURACY',object_id,id FROM measurements WHERE horizontal_accuracy_m IS NULL
UNION ALL
SELECT 'MISSING_SOURCE_REF',object_id,id FROM measurements WHERE NULLIF(btrim(source_ref),'') IS NULL
UNION ALL
SELECT 'BEST_MEASUREMENT_REJECTED_FALLBACK',object_id,measurement_id FROM v_auto_best a JOIN best_policy p USING (object_id) WHERE rejected_fallback AND p.mode='auto';


-- Reference boundaries are populated from versioned shapes by the trusted loader.
CREATE TABLE boundaries (
  ordinal integer PRIMARY KEY, area text NOT NULL, prefix text NOT NULL,
  name text, geom geometry(Geometry,2180) NOT NULL
);
CREATE INDEX boundaries_geom_idx ON boundaries USING gist(geom);
CREATE VIEW v_measurement_regions AS
SELECT m.object_id,m.id,b.area,b.prefix,b.name FROM v_measurements m
LEFT JOIN LATERAL (SELECT area,prefix,name FROM boundaries b
  WHERE ST_Covers(b.geom,m.geom_1992) ORDER BY ordinal LIMIT 1) b ON true;
CREATE VIEW v_geography_issues AS
SELECT CASE WHEN area IS NULL THEN 'MEASUREMENT_OUTSIDE_PL_SK' ELSE 'MEASUREMENT_OUTSIDE_VALLEYS' END code,
  CASE WHEN area IS NULL THEN 'error' ELSE 'warning' END severity, object_id entity_id,id measurement_id,
  NULL::text detail FROM v_measurement_regions WHERE area IS DISTINCT FROM 'valley'
UNION ALL
SELECT 'OBJECT_PREFIX_MISMATCH','warning',b.object_id,b.id,r.prefix FROM v_best b
JOIN v_measurement_regions r ON (r.object_id,r.id)=(b.object_id,b.id)
WHERE r.prefix IS NOT NULL AND split_part(b.object_id,'-',1)<>r.prefix
UNION ALL
SELECT 'MEASUREMENT_DISTANCE_OUTLIER','warning',l.object_id,l.id,
  r.id || ': ' || round(ST_Distance(l.geom_1992,r.geom_1992)::numeric,1)::text || ' m'
FROM v_measurements l JOIN v_measurements r ON l.object_id=r.object_id AND l.history_order<r.history_order
WHERE ST_Distance(l.geom_1992,r.geom_1992)>100;
CREATE VIEW v_domain_warnings AS
SELECT 'CAVE_ID_MISSING_FOR_CAVE_OPENING'::text code,id::text entity_id,NULL::text measurement_id
FROM objects WHERE category='jaskinia_otwor' AND cave_id IS NULL
UNION ALL
SELECT 'NR_INWENT_ON_OBJECT_REFERENCE',object_id,NULL FROM object_external_refs WHERE system='NR_INWENT'
UNION ALL
SELECT 'PIG_CATALOG_REFERENCE_ON_OBJECT',object_id,NULL FROM object_external_refs WHERE system='PIG' AND ref_type IN ('catalog_id','url');
