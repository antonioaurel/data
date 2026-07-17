# 0003 — Retire the wide CSV (`lista-geral-do-mapeamento.csv`)

Status: Accepted

## Context

The normalized model (nodes/edges/aliases → `graph.json` + `content.json`, ADR-0002) was
already the source. But `build.py` still **generated** an inherited wide CSV
(`lista-geral-do-mapeamento.csv`, 6 fields + `Interconexão 1..15`) only because two pages
still read it directly: `diagram.html` and `stats.html`. This kept a third derived artifact
(~400 KB) in the repository — versioned and checked by CI — that nobody edited by hand.

## Decision

Migrate the remaining pages to consume `graph.json` + `content.json` and **remove** the wide
CSV from the project:

- `diagram.html` (pt/en): now builds nodes/edges from the two JSON files (done during the
  diagram migration).
- `stats.html` (pt/en): reconstructs the "wide row" locally (6 fields + `Interconexão 1..15`,
  neighbors sorted and truncated at 15 — the same logic `build.py` used) from the JSON,
  preserving exactly the same fill rates and problem lists.
- `build.py`: removed the generation of `lista-geral-do-mapeamento.csv` (`wide_csv_text`,
  `WIDE_OUT`, `WIDE_HEADER`) and its verification in `--check` mode.
- The `data/lista-geral-do-mapeamento.csv` file was deleted from the repository.

## Consequences

- **Better:** a single derived representation (the two JSON files); ~400 KB fewer versioned
  bytes; CI no longer has to keep a third artifact in sync; a simpler `build.py`.
- **Better:** every page now reads exactly the same source, with no risk of divergence between
  the wide CSV and the JSON.
- **Worse / caveat:** anyone with external tools pointing at the wide CSV must switch to reading
  the JSON (or the Sheet itself). The "one row per node with 15 connection columns" format no
  longer exists as a ready-made artifact.
