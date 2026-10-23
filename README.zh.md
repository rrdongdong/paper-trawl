# research-early-reading

[![CI](https://github.com/rrdongdong/research-early-reading/actions/workflows/ci.yml/badge.svg)](https://github.com/rrdongdong/research-early-reading/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![tests](https://img.shields.io/badge/tests-23%20passing-brightgreen.svg)](./tests)

给 [DSH](https://github.com/deepseek-ai/deepseek-harness) 用的**科研早读技能**：给一个研究方向，
产出一份两篇论文的精读报告——检索、查重、venue 分层、全文精读，最后回填台账。

> **与 DeepSeek 无关。** "DeepSeek Harness (DSH)" 与 "Cordis" 仅作描述性引用。

英文说明见 [README.md](./README.md)。

## 流程

```
方向
 → find_papers.py   arXiv + OpenAlex 双源检索，自动过滤台账已读
 → venue_check.py   给候选打 S/A/B 层级 + 查重   ← 只标注，不否决
 → pdf_fetch / pdf_extract            全文（%%EOF 校验，CID/ObjStm 安全）
 → 8 问精读         内核 / 旧假设 / 最薄证据 / reject 理由 /
                    失效条件 / 迁移代价 / 可严格化口子 / 可证伪预测
 → <MM.DD>早读报告.md + ledger.py add（自动编号，索引与详情同步）
 → 问题卡             cards.py check/emit ← 唯一喂给问题图谱的产物
                    词表 id + 位置 + 证据等级，缺一项 exit 2
 → summarize.py     阶段性文献阅读总结（自动统计 + `[待填]` 判断位）
```

## 唯一的硬约束

**venue 只标注，不否决。** IEEE Trans、RA-L、IJCV、ACM TOG、CVPR/ICCV/NeurIPS/ICML/ICLR、
**ECCV、ICRA、IROS、CVPR-Findings、Workshop、IEEE Access** 都可以读——只是报告里要按层级写明。

唯一会被拦的组合：两篇都是预印本、且层级都不高于 A → 放入 `S*` 待定区等见刊。

| 层级 | 期刊 | 会议 |
|---|---|---|
| **S** | TPAMI、IJCV、TIP、TMM、TNNLS、TKDE、TSE、TRO、TGRS、TCSVT、TVCG | CVPR、ICCV、NeurIPS、ICML、ICLR、AAAI、IJCAI、ACL、MM、SIGGRAPH |
| **A** | **RA-L**、TASE、TII、TITS、TCSS、TDSC、TPDS、TMC、ACM TOG、Pattern Recognition | **ECCV、ICRA、IROS**、CoRL、RSS、3DV、BMVC、WACV、**Findings** |
| **B** | IEEE Access、Sensors、Electronics、Neurocomputing、Information Fusion | Workshop、arXiv |

## 安装

```bash
git clone https://github.com/rrdongdong/research-early-reading.git \
  ~/.dsh/skills/research-early-reading
chmod +x ~/.dsh/skills/research-early-reading/scripts/*.py
```

DSH 会在下次会话把技能载入目录（技能列表在会话启动时注入）。
要求：**Python ≥ 3.9**，无第三方依赖；只有 `find_papers.py` 需要联网（arXiv + OpenAlex，免凭据）。

## 五个脚本

| 脚本 | 作用 | 退出码 |
|---|---|---|
| `find_papers.py --topic "..."` | 双源检索 + 台账过滤 + 层级标注 | 0 成功 / 3 全部已读 |
| `venue_check.py --a-venue … --b-venue …` | 对定稿两篇标注层级并查重 | 0 可用 / 2 双预印本且层级低 / 3 重复 |
| `ledger.py validate\|stats\|add` | 台账校验 / 统计 / 安全追加 | 0 通过 / 2 有问题 / 3 重复 |
| `summarize.py --out file.md` | 文献阅读总结骨架（自动 + `[待填]`） | 0 成功 |
| `cards.py check\|emit report.md` | 解析报告里的「问题卡」块 → 图谱可吃的 JSON | 0 通过 / 2 缺 id/位置/证据等级 |

`ledger.py validate` 不是装饰——首次在真实台账上运行就查出：S11–S13 只在详情表、没进索引，
以及头部累计数与实际条目不符。

## 设计原则

- **查重先于一切**：所有入口都经过台账；`add` 遇到同名或同 ID 直接拒绝（版本走台账 §5，不新增行）。
- **数字必须可追**：报告引用 `Table IV` 这类出处，不推算、不补齐。
- **汇总不替你下结论**：§3（共识/分歧）、§4（路线演进）、§6（阅读路径）固定留 `[待填]`——
  自动生成的综述读起来很专业，实际没有信息。
- **坑即测试**：见 [docs/pitfalls.md](./docs/pitfalls.md)，10 个真实 bug，每个都有对应回归用例。

## 测试

```bash
python3 -m unittest discover -s tests -v     # 22 个用例，不联网，约 0.4 秒
```

## 许可与数据来源

MIT，见 [LICENSE](./LICENSE)。

本仓库**不含任何第三方代码**（仅标准库）与**任何论文全文**。运行时查询 arXiv / OpenAlex / Crossref
并遵守其条款（arXiv 要求请求间隔 ≥3 秒；OpenAlex 元数据为 CC0）。
`references/venues.md` 的 S/A/B 分层是**本项目的编辑判断**，不是 CCF 目录的转载。详见
[THIRD-PARTY-NOTICES.md](./THIRD-PARTY-NOTICES.md)。
