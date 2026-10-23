# research-early-reading

[![CI](https://github.com/rrdongdong/research-early-reading/actions/workflows/ci.yml/badge.svg)](https://github.com/rrdongdong/research-early-reading/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![tests](https://img.shields.io/badge/tests-23%20passing-brightgreen.svg)](./tests)

A [DSH](https://github.com/deepseek-ai/deepseek-harness) (Cordis) **skill**: give it a research
direction, get a two-paper reading report — searched, deduplicated, venue-tiered, fully read, and
folded back into a paper ledger.

> **Not affiliated with DeepSeek.** "DeepSeek Harness (DSH)" and "Cordis" are used descriptively.

中文说明见 [README.zh.md](./README.zh.md)。

---

## What it actually does

```
direction
  → find_papers.py     arXiv + OpenAlex, filter out papers already in the ledger
  → venue_check.py     tier each candidate (S/A/B) + dedup      ← tiers annotate, never veto
  → pdf_fetch / pdf_extract            full text, %%EOF-verified
  → 8-question read    kernel / replaced assumption / weakest evidence / reject reason /
                       failure condition / transfer cost / formalizable opening / falsifiable claim
  → <MM.DD>早读报告.md  + ledger.py add (index row + detail block, auto-numbered)
  → 问题卡 (problem card)                  ← the only artefact that feeds the problem graph
      cards.py check/emit                   vocabulary id + location + evidence grade, or exit 2
  → summarize.py       periodic literature review (auto stats + `[待填]` slots for judgement)
```

## The one hard rule

**venue tier only annotates; it never rejects.** IEEE Trans, RA-L, IJCV, ACM TOG, CVPR/ICCV/NeurIPS/
ICML/ICLR, **ECCV, ICRA, IROS, CVPR-Findings, workshops, IEEE Access** are all readable — the report
just has to say which tier it is.

The only rejection: two preprints with no accepted venue *and* both below tier A → park them in the
`S*` waiting area.

| Tier | Journals | Conferences |
|---|---|---|
| **S** | TPAMI, IJCV, TIP, TMM, TNNLS, TKDE, TSE, TRO, TGRS, TCSVT, TVCG | CVPR, ICCV, NeurIPS, ICML, ICLR, AAAI, IJCAI, ACL, MM, SIGGRAPH |
| **A** | **RA-L**, TASE, TII, TITS, TCSS, TDSC, TPDS, TMC, ACM TOG, Pattern Recognition | **ECCV, ICRA, IROS**, CoRL, RSS, 3DV, BMVC, WACV, **Findings** |
| **B** | IEEE Access, Sensors, Electronics, Neurocomputing, Information Fusion | Workshops, arXiv |

## Install

```bash
git clone https://github.com/rrdongdong/research-early-reading.git \
  ~/.dsh/skills/research-early-reading
chmod +x ~/.dsh/skills/research-early-reading/scripts/*.py
```

DSH picks it up as a skill on the next session (the catalog is injected at session start).
Requirements: **Python ≥ 3.9**, no third-party packages. Network is needed only by
`find_papers.py` (arXiv + OpenAlex, no credentials).

## Preview: a real run

```
$ python3 scripts/find_papers.py --topic "multi-agent active 3D reconstruction" --days 300
[i] 方向：multi-agent active 3D reconstruction
[i] 时间窗：最近 300 天 | 台账已登记标识：17 个

=== 期刊候选（1）===
  ★★☆ 2026-05-11  MAGS-SLAM: Monocular Multi-Agent Gaussian Splatting SLAM
        Accepted to IEEE Transactions on Automation Science and Engineering (T-ASE) 2026
        arXiv:2605.10760v3
```

```
$ python3 scripts/venue_check.py --a-venue "IEEE Robotics and Automation Letters" --a-doi 10.1109/lra.2026.1 \
                                 --b-venue "CVPR 2026 Findings" --b-id arXiv:2605.30342
论文一 [journal/A] 🟡 IEEE/ACM Letters（非 Transactions）：IEEE Robotics and Automation Letters；层级 A，报告中需注明
论文二 [conference/A] 🟡 Findings（主会之外的正式接收轨道）：CVPR 2026 Findings；venue 层级 A，报告中需注明

结论: ✅ 可用（venue 只作标注，不否决）
```

## Tools

| Script | Purpose | Exit codes |
|---|---|---|
| `find_papers.py --topic "..."` | arXiv + OpenAlex search, ledger-filtered, tier-labelled | 0 ok / 3 all known |
| `venue_check.py --a-venue … --b-venue …` | tier + dedup for a chosen pair | 0 ok / 2 both preprints+low / 3 duplicate |
| `ledger.py validate\|stats\|add` | ledger integrity, statistics, safe append | 0 ok / 2 problems / 3 duplicate |
| `summarize.py --out file.md` | literature-review skeleton (auto + `[待填]`) | 0 ok |
| `cards.py check\|emit report.md` | parse the `问题卡` block into card JSON for the problem graph | 0 ok / 2 missing id, location or evidence grade |

`ledger.py validate` is not decorative — on first run against the author's real ledger it found three
`S*` entries present in the detail table but missing from the index, plus a stale header count.

## Design notes

- **Dedup before anything else.** Every path goes through the ledger; `add` refuses a paper whose
  short name or identifier already exists (versions are recorded in the ledger's §5, never as new rows).
- **Numbers must be traceable.** Reports cite `Table IV`-style sources; nothing is inferred or filled in.
- **The summarizer will not write your conclusions.** §3 (consensus/conflict), §4 (route evolution),
  §6 (reading path) are left as `[待填]` on purpose: an auto-generated synthesis reads well and says
  nothing.
- **Pitfalls are tests.** See [docs/pitfalls.md](./docs/pitfalls.md) — ten real bugs, each with the
  regression test that keeps it fixed.

## Tests

```bash
python3 -m unittest discover -s tests -v     # 22 cases, no network, ~0.4 s
python3 -m compileall -q scripts             # syntax gate
```

## Layout

```
SKILL.md                     the skill itself (DSH frontmatter + 6-step protocol)
references/venues.md         tier tables and search channels
references/report-template.md
scripts/find_papers.py       direction → candidates
scripts/venue_check.py       tier + dedup for a pair
scripts/ledger.py            ledger validate / stats / add
scripts/summarize.py         literature-review skeleton
docs/pitfalls.md             10 bugs, each with its test
fixtures/ledger_min.md       test fixture
tests/                       unittest suite
```

## License & data sources

MIT — see [LICENSE](./LICENSE).

This repository contains **no third-party code** (standard library only) and **no paper PDFs**.
It queries arXiv / OpenAlex / Crossref at runtime and respects their terms (arXiv: ≥3 s between
requests; OpenAlex metadata is CC0). The S/A/B tiers in `references/venues.md` are **this project's
editorial judgement**, not a copy of the CCF catalogue. See
[THIRD-PARTY-NOTICES.md](./THIRD-PARTY-NOTICES.md).
