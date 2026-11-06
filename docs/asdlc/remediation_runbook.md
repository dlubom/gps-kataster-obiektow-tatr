# Runbook zakończonej serii PBI-078–086

Serię zakończono w PR #4 i [v1.0.3](verification/v1.0.3.md).
Nowa praca zaczyna się od aktualnego main i osobnej gałęzi; bieżącą
instrukcją jest [dokumentacja operacyjna](../operations.md).

## Wykonanie i lokalna bramka

Aktualna bramka:

```bash
uv sync --frozen
uv run --frozen python scripts/check_project.py --base-ref origin/main
```

Dawne polecenia SQLite oraz szczegóły odbioru zakończonej serii są w
[runbooku z tamtej rewizji](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/13d734213328e5491c1a5c3171e2cb0fdcef705c/docs/asdlc/remediation_runbook.md).
Wyniki poszczególnych napraw zachowują logi wskazane w
[backlogu](backlog_v1.md#naprawy-main-po-przegladzie-2026-10-12).
