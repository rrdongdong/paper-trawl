# Changelog

## 1.1.0 — 2026-10-23

**Problem cards**: every early-read now also produces a machine-readable card, so the
problem graph grows as a side effect of reading instead of as a separate project.

### Added
- `scripts/cards.py` — parse the `### 问题卡 #NN` block out of a report and emit a card
  the graph can ingest
  - `check` / `emit`, `--paper` to pick one card from a multi-paper report
  - refuses (exit 2) on a missing vocabulary id, a missing location, or a missing
    evidence grade — and reports **every** fault in an entry at once instead of one at a time
  - maps `解决 / 遗留 / 假设 / 局限 / 批评 / 异常` to `solves / leaves_open / assumes /
    admits / criticizes / anomaly`; `未对比` marks a criticism as never benchmarked
  - deliberately resolves nothing: mapping a phrase to a canonical id is a human decision,
    because that is where a graph forks one concept into two nodes
- `SKILL.md` step 5.5 + delivery criteria + three new items on the failure list
- `tests/test_cards.py` — 11 tests, including "all faults reported at once" and
  "missing card block is refused"

### Changed
- `scripts/venue_check.py` and `scripts/find_papers.py` synced from the working copy
  (journal acronym support, TRO sub-name stripping, alias normalisation fixes)
- README (en/zh) documents the card step and the evidence-grade wording rule

## 1.0.1 — 2026-10-22

**Renamed** `research-early-reading` → **`paper-trawl`**.

Why: the old name described the *category* (early reading) rather than the *action*. "Trawl" is what
the tool actually does — sweep the literature with a net, keep what is new — and it carries the marine
connotation this project's author works in (underwater robotics), without being a pun that needs
explaining.

Changes: repo/skill name, `metadata.slug`, `metadata.displayName` (Paper Trawl · 拖网早读), README
titles + badges + clone URLs, User-Agent string, `agents/openai.yaml` default prompt.

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
