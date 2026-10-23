# 期刊与会议分层

> **来源与性质说明**
> 本表是**本项目的编辑判断**（S/A/B 为本仓库自定义分层），不是 CCF 官方目录的复制。
> 层级划分参考了中国计算机学会《推荐国际学术会议和期刊目录》等公开的学术评价共识，
> 以及本领域（3DGS / 主动重建 / 水下视觉 / 多机器人）的实际阅读惯例。
> CCF 目录本身由 CCF 发布，本项目**不转载其正文**，只使用"某会议属于 A/B/C 类"这一事实性信息
> 作为标注依据；若需权威定义请查阅 CCF 官方发布物。
> 另：arXiv、OpenAlex、Crossref 的元数据分别遵循其各自的使用条款（arXiv API 要求 ≤1 请求/3 秒；
> OpenAlex 元数据为 CC0）。本项目不缓存、不再分发这些元数据，仅做一次性查询与本地摘要。

> **原则：venue 决定"标注什么"，不决定"能不能读"。**
> 早期版本把 RA-L / ECCV / ICRA / Findings 一律拒收，这是错的——这些正是本领域最好的论文常出现的地方。
> 现在的规则只有一条硬约束：**全文可得 + 与给定方向相关 + 未在台账登记**。venue 只影响报告中的**质量标签**与**选文理由**。

---

## 分层表

| 层级 | 期刊 | 会议 |
|---|---|---|
| **S（旗舰）** | IEEE TPAMI、IJCV、IEEE TIP、IEEE TMM、TNNLS、TKDE、TSE、TRO、TGRS、TCSVT、TVCG | CVPR、ICCV、NeurIPS、ICML、ICLR、AAAI、IJCAI、ACL、ACM MM、SIGGRAPH(Asia) |
| **A（强）** | IEEE RA-L、IEEE TASE、IEEE TII、IEEE TITS、IEEE TCSS、IEEE TDSC、IEEE TPDS、IEEE TMC、ACM TOG、ISPRS J、Pattern Recognition | ECCV、ICRA、IROS、3DV、BMVC、ACCV、WACV、CoRL、RSS、Findings of CVPR/ICCV/NeurIPS |
| **B（可读，需注明）** | IEEE Access、IEEE Sensors J、Remote Sensing、Electronics、arXiv-only（未正式发表） | Workshop（CVPR/ICCV/NeurIPS Workshop）、中文一级学报 |

### 标注规则

- **S**：报告里正常引用，无需额外说明。
- **A**：报告里写一句"venue 层级 A（非 CCF-A，但为本领域主流）"。
- **B**：**必须**在报告中写明"该 venue 层级较低 / 为预印本 / 为 Workshop"，并说明**为什么仍值得精读**（新颖点、方法可迁移、与你方向直接相关）。

---

## 槽位规则（默认，可弹性）

| 槽 | 默认要求 | 弹性 |
|---|---|---|
| **期刊槽** | IEEE Transactions / Journal / **Letters** / ACM Trans / 其他 SCI 期刊 | 无合适期刊时，可用另一篇会议替代，但须在报告开头说明原因 |
| **会议槽** | CCF-A / CCF-B 主会 / **顶会 Findings** | 无合适主会时，可用 Workshop 或期刊替代，同样须说明 |

> **唯一不允许的组合**：两篇都是 arXiv 预印本且都无正式发表记录——这种先降到 `S*` 待定区，等见刊再读。

---

## 明确不建议（不是禁止，是需要理由）

| 情形 | 处理 |
|---|---|
| `IEEE Access` / `Sensors` / `Electronics` 等开放获取刊 | 可读，但标注 B；若同时有同方向的 Trans 版本，优先读 Trans |
| 纯综述（Survey） | 可读，但**不占两个槽位**——综述适合单独一期"综述专读" |
| 同一课题组连发两篇 | 一期最多一篇，避免视野收窄 |
| 中文期刊 | 可读（B 层），但英文顶会有同题时优先英文 |

---

## 检索口径

- **方向驱动**：先用 `scripts/find_papers.py --topic "<方向>"` 拉候选（arXiv + OpenAlex 双源），再人工筛。
- **期刊**：OpenAlex 按 ISSN 过滤（TPAMI `0162-8828`、TIP `1941-0042`、TMM `1941-0077`、TNNLS `2162-237X`、TKDE `1558-2191`、TRO `1941-0468`、TGRS `1558-0644`、RA-L `2377-3766`），Crossref 核卷页。
- **会议**：CVF Open Access（CVPR/ICCV/ECCV/Findings/Workshop）、OpenReview（NeurIPS/ICLR/ICML/CoRL）、ACL Anthology、AAAI/IJCAI proceedings、IEEE Xplore（ICRA/IROS）。
- **预印本**：arXiv API 按关键词 + 日期排序；正式见刊后按台账 §5 追加版本记录。

---

## 判定器

```bash
python3 scripts/venue_check.py --list                       # 看分层表
python3 scripts/venue_check.py \
  --a-venue "IEEE Robotics and Automation Letters" --a-doi "10.1109/lra.2026.1234567" \
  --b-venue "CVPR 2026 Findings" --b-id "arXiv:2605.30342"
```

输出 `role`（journal/conference）+ `tier`（S/A/B），并在 tier≠S 时给出**报告里必须写的那句话**。
