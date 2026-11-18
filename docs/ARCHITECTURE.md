# Notes Sync 架构

## 当前同步流程

日记创建和同步是两条入口。创建任务只补当天缺失的日记。同步任务按配置回看日期范围，默认部署模板在整点触发，手动入口执行同一流程。[创建流程](../src/notes_sync/core/create_diary_workflow.py) · [同步入口](../src/notes_sync/main.py) · [调度模板](../deploy/macos/com.notes-sync.hourly.plist)

1. **读取来源。** 从 Toggl 抓取时间记录，转换为按日期分组的 `Diary`，为没有记录的日期补空对象。取数失败沿现有异常路径终止整轮，不把错误响应当成空数据。
2. **计算日记数据。** Enricher 补充睡眠、天气、步数和统计等信息。睡眠计算会额外读取窗口前一天的 Toggl 记录，失败也会在目标端写入前终止。
3. **逐端决定是否写入。** 分别读取 Notion 和 Obsidian 的日记状态，Guard 决定创建、更新或跳过。已归档日记跳过。如果来源当天返回零条时间记录、目标端已有条目，跳过该端当天的写入，同时保留由时间条目生成的统计。
4. **逐日写入并汇总失败。** Sink Transformer 生成目标端格式，再由 Sink 写入。适配器标记可安全重发的失败，流程等待 5 秒后仅重试该项一次。最终失败仍继续处理其他日期和目标端，结束时汇总失败并以非零状态退出。

[同步流程](../src/notes_sync/core/diary_workflow.py) · [Toggl 取数](../src/notes_sync/infrastructure/sources/toggl/source.py) · [睡眠计算](../src/notes_sync/infrastructure/processors/sleep/enricher.py) · [写入 Guard](../src/notes_sync/core/guard.py) · [退出状态](../src/notes_sync/cli.py)

## 为什么调整写入和重试

2026-11-15，Notion 拒绝了一条超过 2000 字符的 `Time Entries` 富文本。同步流程虽然继续写其他日期和 Obsidian，但最终以非零状态退出。旧 LaunchAgent 对失败进程约每分钟重启一次，每次重新向 Toggl 取数，最终触发 402 限流。旧 Toggl 适配器把 402 转成空列表，导致 11 月 14–16 日两端的时间条目和相关统计被空数据覆盖。11 月 13 日的日记已归档，未被更新。

取数失败会中止写入，写入前也会检查空记录。小时调度模板移除了失败即重启的设置，保留加载时和整点执行。模板变更在重新加载后生效。[写入 Guard](../src/notes_sync/core/guard.py) · [调度模板](../deploy/macos/com.notes-sync.hourly.plist)

## 局部重试规则

流程按 **目标端 × 日期** 处理失败。适配器只有在能确认写入未生效、且适合短暂等待后重发时，才抛出 `RetryableSinkError`。服务特有的限制留在各自的适配器里。[重试契约](../src/notes_sync/core/protocols.py) · [同步流程](../src/notes_sync/core/diary_workflow.py)

| 失败类型 | 处理方式 | 原因 |
|---|---|---|
| 可安全重发的写入失败 | 等待 5 秒，重读失败项的目标状态，再用本轮已有的日记数据决策和写入，最多一次。 | 避免重抓 Toggl、重算统计或重写成功项，并尊重等待期间的创建和归档。 |
| 校验失败或写入结果不明 | 记录目标端、日期和原因，继续处理其他项。 | 重发不能修正无效数据，也可能重复执行已生效的写入。 |
| 来源取数失败 | 读取层仍按现有设置重试。读失败传到流程时，整轮写入中止。 | 获取失败与有效的空记录有不同含义。 |

Notion 适配器在发送前对富文本无损分片，单段最多 2000 字符，每个字段最多 100 段。收到 429 后，等待期间暂停该端后续写入，其他目标端照常处理。[Notion 请求限制](https://developers.notion.com/reference/request-limits) · [Notion 写入](../src/notes_sync/infrastructure/sink/notion/sink.py)

重试状态只在本轮内有效。如果后续需要跨进程补跑，再持久化失败项，并在补跑前重读目标状态和数据。[流程回归测试](../tests/notes_sync/core/test_diary_workflow.py) · [读取重试](../src/notes_sync/core/decorators.py)

## 历史设计草案

以下保留早期接口、状态归约方案与统计计算笔记。当前同步执行顺序和错误处理以上文为准。

## 系统架构

### 数据层 Data Model

```python
class BaseNote(ABC):
    remote_id: Optional[str]
    source: str                    # optional
    content: str                   # optional
    tags: list[str]                # optional
    created_at: datetime           # optional
    updated_at: datetime           # optional
```

### 接口层 Contract

#### Source 接口

```python
class BaseSource(ABC):
    @abstractmethod
    def fetch_raw_data(self, url: str, start_date: datetime, end_date: datetime, timezone: timezone = local_tz, tokens: str = None) -> Any:
        """负责 I/O: 从 API 或文件读取原始数据"""
        pass
```

#### Source_Transformer 接口

```python
class BaseSourceTransformer(ABC):
    @abstractmethod
    def to_internal_model(self, raw_data: Any) -> list[BaseNote]:
        """负责解耦: 将原始 JSON 转为系统内部的 Note/Diary 对象"""
        pass
```

#### Sink_Transformer 接口

```python
class BaseSinkTransformer(ABC):
    @abstractmethod
    def to_sink_format(self, internal_model: list[BaseNote]) -> Any:
        """负责解耦: 将系统内部的 Note/Diary 对象转为目标端需要的格式(Markdown, JSON等)"""
        pass
```

#### Sink 接口

```python
class BaseSink(ABC, tokens: str = None):
    @abstractmethod
    def sink_data(self, formatted_data: Any):
        """负责 I/O: 将格式化后的数据保存到文件或调用API"""
        pass
```

### 数据流

Source -> Source_Transformer -> Sink_Transformer -> Sink

1. BaseSource 接口
   从不同数据源读取原始数据, 目前只支持 Toggl
   用户可以自己扩展到各种网络来源(API, MCP, SDK 等), 本地数据(文件,数据库等)

2. BaseSourceTransformer 前端接口
   将不同数据源原始数据转为系统内部的具体对象(如 Note)

3. BaseSinkTransformer 后端接口
   将 Note 和 TimeEntry 数据转为不同数据源保存格式

4. BaseSink 接口
   将数据保存到不同数据源, 目前只支持 Obsidian, Notion
   用户可以自己扩展到各种网络来源(API, MCP, SDK 等), 本地数据(文件,数据库等)

#### 异常处理

1. 当 BaseSource / BaseSink 实现类 读取/写入数据失败时, 需要写 sync 日志
   1.1 网络原因, 需要重试 1 次
   1.2 其他原因, 不重试
   1.3 对应父类处理
   1.4 日志内容包括, 失败时间, 实现类的类型和接口, 具体参数, 错误原因
2. 当 BaseSourceTransformer / BaseSinkTransformer 实现类, 转换数据出现异常时, 需要写 sync 日志
   2.1 对应父类需要捕获异常
   2.2 日志内容包括, 失败时间, 实现类的类型和接口, 具体参数(含输入数据), 错误原因

### 具体类

```python
class Diary:
    date: datetime
    time_entries: list[TimeEntry]
    report: DiaryReport
```

```python
class DiaryReport:
    # Summary data
    summary: str
    steps: int
    sleep: SleepReport
    weather: WeatherReport
    # ... other derived stats
```

```python
class DiarySyncContext:
    """Represents remote state for synchronization"""
    remote_id: Optional[str]
    status: Optional[str]
    steps: Optional[int]
    # ...
```

```python
class TimeEntry(BaseNote):
    start: datetime
    end: datetime
    duration: int     # optional
    category: str     # optional
    sub_category: str     # optional
```
