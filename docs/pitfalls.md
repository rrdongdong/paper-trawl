# 踩过的坑（每条都有一条对应测试）

这个技能的四个脚本都是"用真实数据跑过、并因此改过错"的。下面每一条都对应 `tests/` 里的一个用例，
改动时**不要削弱这些断言**。

## 1. 期刊层级不能按裸词匹配

`Journal of Medical Imaging`（SPIE 出版）曾被判成 ★★★，只因为 S 层清单里有裸词 `medical imaging`。

**修法**：只有 `IEEE/ACM Transactions on <副名>` / `IEEE Journal of <副名>` 才按副名查表；
独立期刊走单独的名字清单；含易混淆裸词但不在清单的，一律交人工（tier=`?`）。

测试：`JournalTiers.test_medical_imaging_journal_is_not_flagship`

## 2. 副名要归一化

`IEEE Transactions on Robotics` 抽出的副名是 `robotics`，而清单里存的是 `transactions on robotics`，
导致 TRO 掉到 A 层。

**修法**：列表定义后统一 `_strip_prefix()` 去掉 `transactions on / journal of` 前缀。

测试：`JournalTiers.test_flagship_transactions_are_S`

## 3. `Letters` 是期刊，不是会议

`IEEE Robotics and Automation Letters` 曾被别名 `robotics and automation` 抢先匹配成会议。

**修法**：删掉过宽别名；期刊判定提到会议判定之前；单独处理 `*Letters` → journal / A。

测试：`JournalTiers.test_letters_is_journal_A_not_conference`

## 4. 会议全称会被期刊表吞掉

`IEEE/CVF Conference on Computer Vision and Pattern Recognition` 含子串 `pattern recognition`，
而 `Pattern Recognition` 是 A 层独立期刊 → CVPR 被误判成期刊。

**修法**：先做"会议语境"判定（含 conference/proceedings/workshop/symposium 就直接走会议分支）。

测试：`ConferenceTiers.test_spelled_out_venue_names`

## 5. 拒绝词必须优先于主会名

`CVPR 2026 Findings` 含 `cvpr`，若先匹配主会就会得到 ★★★（错，Findings 是另一条轨道）；
`CVPR 2026 Workshops` 同理。

**修法**：会议语境内的判定顺序固定为 **Workshop → Findings/ECCV/ICRA… → 主会**。

测试：`ConferenceTiers.test_findings_is_not_main_conference`、`test_reject_words_beat_venue_words`

## 6. 复数形式

`Workshops` 不被 `\bworkshop\b` 命中（s 是词字符）。

**修法**：`norm()` 里做一次复数归一（workshops→workshop）。

测试：`test_reject_words_beat_venue_words`

## 7. `&` 与 `and`

`IEEE/RSJ International Conference on INTELLIGENT ROBOTS & SYSTEMS` 里的 `&` 导致 IROS 匹配失败。

**修法**：`norm()` 把 `&` 展开成 ` and `。

测试：`ConferenceTiers.test_ampersand_normalisation`

## 8. 查重脚本曾把表格栏目当成论文简称

`paper_dedup.py` 把台账 §3（5 列）的第 3 列当成"简称"，而那一列是"出处"，值是 `arXiv 等`，
于是**任何 arXiv ID 都被误判为重复**。

**修法**：简称只取 §1 的 8 列正式行，并过滤 `arxiv/doi/ieee` 等出版渠道词。

（该脚本在 DSH 工作区的 `tools/paper_dedup.py`，不属于本仓库；这里记录原因。）

## 9. 台账的索引与详情会脱节

脚本 `ledger.py validate` 首次运行即在真实台账上报出：S11–S13 只存在于 §3 详情表、
没进 §1 索引。

**修法**：`validate` 同时比对 §1 与 §2 的双向一致性、编号连续性、头部累计数、以及 §3→§1 的覆盖。

测试：`test_ledger.CliBehaviour.test_validate_catches_missing_index_row`、
`test_validate_catches_head_count_drift`

## 10. 汇总不能替人下结论

`summarize.py` 若自动生成"共识/分歧"，就会产出看起来很专业但无证据的假综述。

**设计**：§3/§4/§6 固定留 `[待填]`，只给格式提示；自动部分仅限统计与台账摘录。

测试：`test_summarize.Summarize.test_generates_sections_and_keeps_judgement_empty`

## 11. "查不了"不等于"重复"

`venue_check.py` 在找不到 `tools/paper_dedup.py` 与 `论文台账.md` 时曾返回"重复"（exit 3），
把一次**环境缺失**误报成**论文重复**。

**修法**：缺台账时放行并打印「跳过查重」，只有在真的读到台账并命中时才 return 3。

测试：`DedupSemantics.test_missing_ledger_does_not_fail_the_pair`
