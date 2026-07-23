# 项目重构标准

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
