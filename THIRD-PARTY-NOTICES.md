# 第三方与数据来源说明

本仓库**不包含任何第三方源代码**。

## 运行时依赖

无。所有脚本与测试仅使用 Python 标准库（`urllib`、`json`、`re`、`unittest` 等）。

## 外部数据源（仅运行时查询，不缓存、不再分发）

| 源 | 用途 | 条款要点 |
|---|---|---|
| arXiv API（`export.arxiv.org`） | 检索预印本 | 官方要求相邻请求间隔 ≥3 秒；`find_papers.py` 已遵守（串行 + 3s，User-Agent 可配联系方式） |
| OpenAlex（`api.openalex.org`） | 检索期刊论文元数据 | 元数据以 CC0 发布 |
| Crossref（`api.crossref.org`） | 核验 DOI / 卷页 | 元数据开放使用 |

**本项目不分发论文全文**。台账只保存引用信息（标题/出处/链接）与作者自己写的摘要与判断；
PDF 全文由使用者通过各自渠道获取，仓库内不含任何论文文件。

## 内容来源

- `references/venues.md` 的 S/A/B 分层是**本项目的编辑判断**，参考了学术界的公开评价共识
  （含 CCF 推荐目录所体现的 A/B/C 事实性信息）与本领域的阅读惯例；**未转载 CCF 目录正文**。
- `SKILL.md`、`references/report-template.md`、`docs/pitfalls.md`、各脚本与测试均为原创。

## 商标

"DeepSeek"、"DeepSeek Harness (DSH)"、"Cordis"、"GitHub" 等为其各自所有者的商标，
本项目仅在描述兼容性与用途时作**陈述性使用**，不表示任何隶属、赞助或背书关系。
