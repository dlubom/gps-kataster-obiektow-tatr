-- Parameters are extracted source values, never executable historical SQL.
WITH old_objects AS (
    SELECT value->>'id' AS id, value->>'path' AS path,
           value->'measurements' AS measurements, ordinality AS object_order
    FROM jsonb_array_elements(%s::jsonb) WITH ORDINALITY
), new_objects AS (
    SELECT value->>'id' AS id, value->>'path' AS path, value->'measurements' AS measurements
    FROM jsonb_array_elements(%s::jsonb)
), old_measurements AS (
    SELECT o.id AS object_id, m.value->>'id' AS id, m.value->'source' AS source,
           m.ordinality AS history_order, o.object_order
    FROM old_objects o, jsonb_array_elements(o.measurements) WITH ORDINALITY m
), new_measurements AS (
    SELECT o.id AS object_id, m.value->>'id' AS id, m.value->'source' AS source,
           m.ordinality AS history_order
    FROM new_objects o, jsonb_array_elements(o.measurements) WITH ORDINALITY m
), findings AS (
    SELECT 'HISTORY_OBJECT_DELETED' AS code, o.path,
           'Historical object ' || o.id || ' was removed.' AS description,
           o.object_order, 0::bigint AS issue_order
    FROM old_objects o LEFT JOIN new_objects n USING (id) WHERE n.id IS NULL
    UNION ALL
    SELECT CASE WHEN n.id IS NULL THEN 'HISTORY_MEASUREMENT_DELETED'
                ELSE 'HISTORY_MEASUREMENT_CHANGED' END,
           obj.path,
           CASE WHEN n.id IS NULL
                THEN 'Historical measurement ' || o.object_id || '/' || o.id || ' was removed.'
                ELSE 'Native geometry or elevation/datum changed for ' || o.object_id || '/' || o.id || '; append a correction.' END,
           o.object_order, o.history_order
    FROM old_measurements o JOIN new_objects obj ON obj.id = o.object_id
    LEFT JOIN new_measurements n ON n.object_id = o.object_id AND n.id = o.id
    WHERE n.id IS NULL OR o.source IS DISTINCT FROM n.source
    UNION ALL
    SELECT 'HISTORY_ORDER_CHANGED', n.path,
           'Historical measurement order changed for ' || o.id || '; new measurements must be appended.',
           o.object_order, 9223372036854775807::bigint
    FROM old_objects o JOIN new_objects n USING (id)
    WHERE EXISTS (
        SELECT FROM old_measurements a JOIN new_measurements b USING (object_id, id)
        WHERE a.object_id = o.id AND a.history_order <> b.history_order
    ) AND NOT EXISTS (
        SELECT FROM old_measurements a LEFT JOIN new_measurements b USING (object_id, id)
        WHERE a.object_id = o.id AND b.id IS NULL
    )
)
SELECT code, path, description FROM findings ORDER BY object_order, issue_order;
