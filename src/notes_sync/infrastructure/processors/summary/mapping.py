from enum import StrEnum


class CategoryKey(StrEnum):
    FOCUS = "Focus"
    PLAY = "Play"
    SLEEP = "Sleep"
    ROUTINE = "Routine"
    RECHARGE = "Recharge"
    OTHERS = "Others"
    UNRECORDED = "Unrecorded"
    MAINTAIN = "Maintain"


STATISTICS_LABELS = {
    CategoryKey.FOCUS: "🎯 专注",
    CategoryKey.PLAY: "🕹️ 玩耍",
    CategoryKey.SLEEP: "💤 睡眠",
    CategoryKey.ROUTINE: "🧱 琐事",
    CategoryKey.RECHARGE: "⚡ 充电",
    CategoryKey.OTHERS: "📦 其他",
    CategoryKey.UNRECORDED: "❓ 空白",
    CategoryKey.MAINTAIN: "🔧 维护",
}


class LabelKey(StrEnum):
    BED_TIME_PREV = "🌙 昨晚就寝"
    UP_TIME = "☀️ 今日起床"
    STEPS = "🚶 步数"
    LINGER_MINUTES = "🛌 赖床分钟"
