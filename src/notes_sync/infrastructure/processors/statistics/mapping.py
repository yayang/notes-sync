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


# 映射 Activity (Toggl Project) → 分类的规则
_ACTIVITY_RULES = {
    CategoryKey.PLAY: ["🍿 被动娱乐"],
    CategoryKey.SLEEP: ["💤 Sleep"],
    CategoryKey.ROUTINE: ["🏠 家务通勤", "🚿 洗漱护肤"],
    CategoryKey.RECHARGE: [
        "🏋️ Fitness",
        "🏞️ Outing 主动",
        "🥂 Social",
    ],
    CategoryKey.MAINTAIN: ["🔧 Maintenance", "📥 必要杂事"],
    CategoryKey.FOCUS: [
        "✍️ Creation",
        "💻 Develop",
        "🎯 Job Hunt",
        "🎓 学习,体系化",
        "📖 Reading",
    ],
}


class AreaLabel:
    """Toggl Client names that map to Areas."""

    LIFE = "❤️ LIFE"
    HEALTH = "💪 HEALTH"


# 用于 breakdown 中缺失活动名的兜底
NO_ACTIVITY_LABEL = "No Activity"

# 反向索引: Activity → Category (O(1) 查找)
ACTIVITY_TO_CATEGORY: dict[str, CategoryKey] = {
    activity: cat
    for cat, activities in _ACTIVITY_RULES.items()
    for activity in activities
}
