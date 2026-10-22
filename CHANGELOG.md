# Changelog

## 1.0.0 — 2026-10-22

First public release as a standalone repository.

### Contents
- `SKILL.md` — DSH skill (frontmatter + 6-step protocol: search → tier → read → 8 questions →
  report → ledger/summary).
- `scripts/find_papers.py` — direction → candidates via arXiv + OpenAlex, ledger-filtered, tier-labelled.
- `scripts/venue_check.py` — S/A/B tiering **without vetoing**, plus dedup against the ledger.
- `scripts/ledger.py` — `validate` / `stats` / `add`; `add` refuses duplicates and keeps the index and
  detail sections in sync.
- `scripts/summarize.py` — literature-review skeleton: auto statistics + `[待填]` slots for judgement.
- 22 unit tests (`python3 -m unittest discover -s tests`), no network required.
- `docs/pitfalls.md` — ten real bugs, each pinned by a regression test.

### Deliberate non-goals
- The summarizer never writes consensus/conflict conclusions: an auto-generated synthesis reads well
  and says nothing.
- Venue tiering never blocks a paper on tier alone; only two preprints below tier A are parked.
