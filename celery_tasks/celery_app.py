from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# 创建Celery应用实例
celery_app = Celery(
    "azure_advisor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "celery_tasks.tasks.intent_tasks",
        "celery_tasks.tasks.title_tasks",
        "celery_tasks.tasks.log_tasks"
    ]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # 减少预取，适合较重的任务
    task_acks_late=True,  # 任务完成后再确认，提高可靠性
)

# 方便在其他地方导入celery应用
def get_celery_app():
    return celery_app