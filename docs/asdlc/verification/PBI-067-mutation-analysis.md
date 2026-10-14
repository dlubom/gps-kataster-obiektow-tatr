# PBI-067 — Ocena 12 ocaleń

Baza `c460c2cf48dbfbdfe2405553d724346c83a1ba1a`. Dokładnie 358 identycznych ID/diffów: baseline 196 killed / 162 survived, final 346 killed / 12 survived. 150 nowych killed, brak regresji; wszystkie 14 krytycznych ID killed, w tym pięć z karty było survived na bazie.

Poza zakresem pozostaje pełna kampania serii PBI-054. Nie deklarujemy 100% projektu ani globalnej ekwiwalencji dla błędnych rekordów. Wszystkie diffy i raw metadata są w [rejestrze](PBI-067-mutations.json).

## gps_kataster_obiektow_tatr.validator.x__validate_duplicate_tpn_globalids__mutmut_33

cosmetic: Only the separator between described file paths changes; exact code, ERROR, both owner paths and every path token are asserted.

## gps_kataster_obiektow_tatr.validator.x__validate_cross_references__mutmut_58

equivalent_for_schema_valid_ids: Object schema permits one hyphen between prefix and numeric counter. split limit or rsplit gives the same durable prefix on that domain; malformed multi-hyphen IDs remain schema errors.

## gps_kataster_obiektow_tatr.validator.x__validate_cross_references__mutmut_59

equivalent_for_schema_valid_ids: Object schema permits one hyphen between prefix and numeric counter. split limit or rsplit gives the same durable prefix on that domain; malformed multi-hyphen IDs remain schema errors.

## gps_kataster_obiektow_tatr.validator.x__validate_cross_references__mutmut_61

equivalent_for_schema_valid_ids: Object schema permits one hyphen between prefix and numeric counter. split limit or rsplit gives the same durable prefix on that domain; malformed multi-hyphen IDs remain schema errors.

## gps_kataster_obiektow_tatr.validator.x__validate_cross_references__mutmut_93

description_limit: Prefix override reason diagnostics are an earlier rule outside the reference/attachment/distance regressions. ERROR/code/path remain tested. Free description (including None for 93) is an explicit reporting coverage limit for PBI-054, not claimed equivalent.

## gps_kataster_obiektow_tatr.validator.x__validate_cross_references__mutmut_100

description_limit: Prefix override reason diagnostics are an earlier rule outside the reference/attachment/distance regressions. ERROR/code/path remain tested. Free description (including None for 93) is an explicit reporting coverage limit for PBI-054, not claimed equivalent.

## gps_kataster_obiektow_tatr.validator.x__validate_cross_references__mutmut_101

description_limit: Prefix override reason diagnostics are an earlier rule outside the reference/attachment/distance regressions. ERROR/code/path remain tested. Free description (including None for 93) is an explicit reporting coverage limit for PBI-054, not claimed equivalent.

## gps_kataster_obiektow_tatr.validator.x__validate_object_attachments__mutmut_10

schema_guarded_default: Attachment.id is required by schema, so this default cannot affect a schema-valid record. No global claim for malformed records or private helper callers.

## gps_kataster_obiektow_tatr.validator.x__validate_object_attachments__mutmut_12

schema_guarded_default: Attachment.id is required by schema, so this default cannot affect a schema-valid record. No global claim for malformed records or private helper callers.

## gps_kataster_obiektow_tatr.validator.x__validate_object_attachments__mutmut_15

schema_guarded_default: Attachment.id is required by schema, so this default cannot affect a schema-valid record. No global claim for malformed records or private helper callers.

## gps_kataster_obiektow_tatr.validator.x__validate_object_attachments__mutmut_16

schema_guarded_default: Attachment.id is required by schema, so this default cannot affect a schema-valid record. No global claim for malformed records or private helper callers.

## gps_kataster_obiektow_tatr.validator.x__validate_object_attachments__mutmut_22

schema_invalid_diagnostics_limit: The branch requires a non-string Attachment.path, already a schema ERROR. Valid URL followed by missing local path is tested separately. On malformed records break can omit later diagnostic detail; schema still blocks. Outside the schema-valid fixture scope; not globally equivalent.
