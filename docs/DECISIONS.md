# Architectural Decision Records

This file records non-trivial design choices. New entries append at the bottom.
Format: [ADR MADR-lite](https://adr.github.io/madr/).

---

## ADR-0001 — Replace Pandera with a polars-native validator

- **Status:** accepted
- **Date:** 2026-04-14
- **Supersedes:** original `.claude/rules/python.md` line naming Pandera.

### Context

RegScope's architecture rules forbid `pandas` (polars is the dataframe of
record) but the original Python rule required `pandera` for DataFrame schema
validation at pipeline boundaries.

`pandera.polars`, despite being the polars-native entry point, unconditionally
imports `pandas` through its shared `schema_statistics` module. Installing
`pandera[polars]` therefore requires pulling pandas (~55 MB installed) into
every RegScope container, into CI, and into developer environments. This
violates the spirit of the "no pandas" architecture rule even though pandas
code is not written by us.

Auditing the schemas RegScope needs across its roadmap (raw/processed
comments, `duplicate_groups`, `clusters`) shows only four simple invariants
per schema: presence, dtype, nullability, uniqueness. None of Pandera's
advanced features (cross-column checks, coercion, typing integration,
hypothesis integration) are used or planned.

### Decision

Drop `pandera[polars]` from `pyproject.toml`. Introduce `data/validation.py`
with a single `validate(frame, *, required, unique, non_null, strict)` helper
that covers RegScope's needs in ~30 lines of polars. Each boundary module
exports a thin `validate_<table>(frame)` function wrapping it.

### Consequences

**Positive**

- No pandas anywhere in the dependency graph. Smaller images, faster cold
  starts, smaller CVE surface, and the "we are a polars shop" story holds
  both culturally and in the lockfile.
- Validator behavior is owned by us — error messages, ordering of checks,
  and extensions are under our control.
- One less young third-party integration (`pandera.polars`) whose
  compatibility surface still churns.

**Negative**

- We give up Pandera's declarative DSL and richer error reporting. Error
  messages are now plain strings; extension (e.g., conditional checks)
  requires writing code.
- If post-MVP schemas grow complex (cross-column invariants, coercion
  pipelines), we may want to revisit. Swapping back to a validator library
  later is a localized change — boundaries call `validate_<table>` rather
  than Pandera directly, which keeps the blast radius small.

**Follow-ups**

- Updated `.claude/rules/python.md` and `.claude/rules/data-pipeline.md` to
  reference `data.validation.validate` instead of Pandera.
- Future maintainers: do not re-add Pandera without first revisiting this
  ADR. If genuinely needed, prefer a polars-native alternative (e.g.,
  `patito`) that does not pull pandas.
