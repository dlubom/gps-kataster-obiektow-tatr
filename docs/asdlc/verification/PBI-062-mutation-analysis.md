# PBI-062 — analiza ocaleń

Zakres: 299 mutantów ośmiu funkcji TPN. Final: 275 killed / 24 survived.
Każdy z 24 wskazanych krytycznych mutantów jest killed. Nie jest to pełna
kampania projektu ani zamknięcie PBI-054. Brak pending/timeout/no tests/tool error
w wybranym zakresie; 9919 pozostałych wygenerowanych ID nie jest oceniane tutaj.

Pełne diffy, raw codes, mapowanie testów, czasy i fingerprinty są w
[PBI-062-mutations.json](PBI-062-mutations.json). Poniższe oceny dotyczą
obecnego publicznego buildera i zachowują jawne granice.

## x__match_tpn_row__mutmut_55

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_58

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_63

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_64

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_65

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_66

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_67

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_74

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_86

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_87

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_88

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_109

equivalent_under_prefiltered_name_distance_invariant — The caller already filters every candidate by the same name and radius. One candidate returns before name is read; two or more stay unresolved whether the second name filter sees all or zero. Changing this helper argument has no effect through the current public builder. Not equivalence for arbitrary direct helper calls.

## x__match_tpn_row__mutmut_112

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_124

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_125

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_126

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__match_tpn_row__mutmut_127

unobservable_internal_new_status — After unresolved and match handling, the public builder treats any remaining no-match outcome as a new proposal. The internal status spelling is not exposed; public row status stays new. Not a claim for future consumers of the private outcome.

## x__match_tpn_row__mutmut_128

unobservable_internal_new_status — After unresolved and match handling, the public builder treats any remaining no-match outcome as a new proposal. The internal status spelling is not exposed; public row status stays new. Not a claim for future consumers of the private outcome.

## x__match_tpn_row__mutmut_129

unobservable_internal_new_status — After unresolved and match handling, the public builder treats any remaining no-match outcome as a new proposal. The internal status spelling is not exposed; public row status stays new. Not a claim for future consumers of the private outcome.

## x__choose_candidate_by_distance_or_name__mutmut_47

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__choose_candidate_by_distance_or_name__mutmut_50

diagnostic_description_coverage_limit — Changes or drops the human-readable explanation; asserted status, machine-readable issue code, target and retained payload stay correct. Tests deliberately do not pin exact prose. This remains a diagnostic coverage limit for final PBI-054, not global equivalence.

## x__infer_tpn_object_category__mutmut_4

category_default_equivalent_for_current_rules — The CSV table supplies GENEZA (possibly empty); if absent, None normalizes to empty and XXXX adds no category keyword. The explicit separator prevents joining a category token across the two inputs. Known category priority and outputs are unchanged; no claim for future category vocabulary.

## x__infer_tpn_object_category__mutmut_6

category_default_equivalent_for_current_rules — The CSV table supplies GENEZA (possibly empty); if absent, None normalizes to empty and XXXX adds no category keyword. The explicit separator prevents joining a category token across the two inputs. Known category priority and outputs are unchanged; no claim for future category vocabulary.

## x__infer_tpn_object_category__mutmut_9

category_default_equivalent_for_current_rules — The CSV table supplies GENEZA (possibly empty); if absent, None normalizes to empty and XXXX adds no category keyword. The explicit separator prevents joining a category token across the two inputs. Known category priority and outputs are unchanged; no claim for future category vocabulary.
