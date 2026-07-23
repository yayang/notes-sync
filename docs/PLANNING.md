结论：`notes-sync` V2 架构的核心是从 **单向线性管道 (Pipeline)** 演进为 **状态归约引擎 (State Reducer)**。通过将 `Context` 从末端验证环节前移至前端输入环节，将同步的本质从“覆盖数据”转变为“对齐状态”，彻底解决信息丢失与逻辑断层问题。

---

## 1. 架构演进说明

### 旧架构：线性管道模式 (Linear Pipeline)

- **流程：** `Source` → `Transform` → **`Enricher`** → `Guard (Check Context)` → `Sink`
- **缺陷：** `Enricher` 处于信息真空。若 `Source` (Toggl) 缺失步数或状态，`Enricher` 无法感知 `Sink` (Notion) 中的现有值，导致生成的 AI 摘要错误或关键字段被误删。

### 新架构：状态归约模式 (State Reducer)

- **流程：** **`(Source + Sink Contexts)`** → `Reducer` → **`Enricher`** → `Sink`
- **优势：** `Enricher` 具备上帝视角。它处理的是经过 `Reducer` 仲裁补全后的“唯一权威事实（Master Diary）”。

---

## 2. 核心组件重定义

### 2.1 Source Providers (多源输入)

- **组成：** 包含 `TogglSource` (新事件) 以及从原 `Sink` 目录迁移而来的 `NotionContextSource` 与 `ObsidianContextSource` (当前状态)。
- **职责：** 并行抓取原始数据。每个 `Source` 必须提供字段内容及对应的 **时间戳 (updated_at)**。

### 2.2 Reducer (仲裁与合并)

- **职责：** 承担 `SourceProviders` 产出的 `Diary` 组与 `Contexts` 组的合成工作。
- **吸收规则：** 基于 **字段级优先级 (Field-Level Priority)** 实现归约。
- **优先级仲裁：** 例如 `Steps` 字段规则为 `[Toggl, Notion]`。若 Toggl 无数据，则自动吸收旧数据中的最大值。
- **冲突解决：** 引入 **最后写入者胜 (LWW)** 策略。若两端数据不一致，对比 `updated_at`，以最新修改为准。

- **产出：** 唯一的 `Master Diary` 对象，它是所有 `Enricher` 的唯一输入。

### 2.3 Enricher (单次高阶加工)

- **职责：** 仅处理 `Reducer` 产出的 `Master Diary`。
- **逻辑：** 严禁访问原始 `Contexts`。由于输入已经是“补全后的事实”，`SummaryEnricher` 生成的摘要将具备跨平台的一致性。
- **效能：** 每个日期仅执行一次，避免冗余的 AI 接口调用与计算。

### 2.4 Sink Providers (身份感知写入)

- **身份逻辑：** 依然持有 `Context`，但仅用于 **Identity (身份)** 识别。
- 依据 `Context` 中的 `page_id` 或 `file_path` 判定执行 `Create` 还是 `Update`。

- **轻量 Guard：** 内化为“写避让”逻辑。执行 `Deep Compare`，若 `Master Diary` 与 `Initial Context` 无差异，则直接终止写入。

---

## 3. 效能逻辑判定 (Efficiency & Utility)

- **确定性导向：** 通过 `Reducer` 的仲裁，系统从“搬运工”进化为“状态机”。即使某端同步中断（如 Notion 宕机），只要 Obsidian 有记录，系统就能通过 `Reducer` 实现逻辑自愈。
- **止损建议：** 这种架构以极小的 `Source` 读取开销（仅读取 Metadata），换取了对全链路不确定性的消除，边际收益极大。
- **分工明确：** `Source` 负责取，`Reducer` 负责选，`Enricher` 负责写（摘要），`Sink` 负责存。

---

## 4. 总结

**分布式数据同步问题的标准解法。** “Context 前提”不仅解决了步数缺失的 Bug，更重要的是它建立了一套 **冲突解决机制**。现在的系统不再依赖 `Source` 的绝对完美，而是具备了从现有存储中“恢复记忆”的能力。这标志着项目从脚本层级跃迁到了系统层级。

---

**下一步执行 (Procedural Execution):**
`Diary` 类中新增的 `absorb` 方法以及 `Reducer` 的核心代码实现，它将定义如何配置不同字段的优先级。

---

## 5. Bug Fix: StatisticsEnricher Unrecorded 计算错误

### 根因

`StatisticsEnricher._process_entries` 用**各条目时长算术求和**来推算未记录时间：

```python
unrecorded = max(total_day_seconds - recorded_seconds, 0)
```

当日记存在**重叠时间段**时（例如同一天同时记录了两个并发活动），重叠部分被重复累加，导致 `recorded_seconds > 86400`，`unrecorded` 被 `max(..., 0)` 强制截断为 `0`。

### 正确语义

"Unrecorded" = **一天内没有任何条目覆盖的时间片段之和**，本质是集合补集，而非算术。

### 修复方案：计算空隙（Gap-based）

1. 收集所有时间条目的 `(start, end)` 区间列表。
2. 对区间列表做 **merge intervals**（排序后贪心合并重叠段）。
3. 在 `[day_start, day_end]` 内，找出合并区间之外的空隙，累加空隙时长即为真正的 `unrecorded`。

**伪代码：**

```python
def __calc_unrecorded_seconds(self, intervals, day_start, day_end) -> float:
    if not intervals:
        return (day_end - day_start).total_seconds()
    merged = _merge(sorted(intervals))          # 合并重叠区间
    gaps = []
    cursor = day_start
    for s, e in merged:
        s, e = max(s, day_start), min(e, day_end)   # 裁剪到当天范围
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < day_end:
        gaps.append((cursor, day_end))
    return sum((e - s).total_seconds() for s, e in gaps)
```

**优势：**

- 重叠区间不会被重复扣除。
- 未来若需展示"哪些时段没有记录"，空隙列表天然可用。

### 改动范围

- `src/notes_sync/infrastructure/processors/statistics/enricher.py`
  - `_process_entries`：改为收集区间列表，调用 gap 计算替换原算术逻辑。
  - 新增私有方法 `__calc_unrecorded_seconds` 与 `__merge_intervals`。
- 不影响 `CategoryReport`、`mapping.py` 及任何 Sink/Source。
