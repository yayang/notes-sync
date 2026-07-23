import logging
import time
from functools import wraps

from notes_sync.config.settings import get_settings

logger = logging.getLogger(__name__)


def retry_on_exception(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        limit = getattr(self, "limit", None)
        delay = getattr(self, "delay", None)

        if limit is None:
            limit = get_settings().retry.limit
        if delay is None:
            delay = get_settings().retry.delay

        for i in range(limit + 1):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if i >= limit:
                    raise e
                logger.warning(f"Retrying {i + 1}...")
                time.sleep(delay)

    return wrapper


def login_required(func):  # 第一层：直接拿函数
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 👉 假设 args[0] 是 self, 且 self.user 存在
        # 或者从全局上下文拿到 current_user
        user = getattr(args[0], "user", None)

        if not user or not user.is_authenticated:
            raise PermissionError("请先登录！")  # 🚫 拦截！不执行原函数

        return func(*args, **kwargs)  # ✅ 放行

    return wrapper


def requires_role(role_name):  # 🏭 第一层：收参数 (admin)
    def decorator(func):  # 🎁 第二层：收函数
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 👉 拿到用户
            user = getattr(args[0], "user", None)

            # 👉 核心校验逻辑
            if user.role != role_name:
                raise PermissionError(f"你不是 {role_name}，走开！")

            return func(*args, **kwargs)

        return wrapper

    return decorator
