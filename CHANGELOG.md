# Changelog

## 0.2.0

### Added

- `similarity.py`: Jaccard similarity on task domain features combined with
  complexity distance and task-type matching. Weighted nearest-neighbour voting
  selects the model that performed best on the most similar historical tasks.
- `recommend` CLI command: accepts `--task-file` (harness task JSON with a
  `features` field) or `--features` (raw JSON string) and `--top-k`.
- `fetch_reference_corpus()` on `Database`: joins tasks, runs, and scores to
  produce a scored reference corpus for similarity lookup.
- `features_json` column on the `tasks` table with automatic safe migration for
  pre-v0.2 databases (ALTER TABLE guarded by a try/except).
- `py.typed` marker for downstream type-checking support.
- `LICENSE` (MIT).

### Changed

- Removed `authors` field from `pyproject.toml`.
- Added `classifiers` and `keywords` to `pyproject.toml`.
- Updated roadmap and limitations to reflect v0.2 state.

## 0.1.0

Initial release. Full benchmark pipeline (planner → harness → scoring →
reports), SQLite persistence, deterministic scoring, Markdown and JSON report
generation, plan ingestion, export in JSONL/JSON/CSV.
