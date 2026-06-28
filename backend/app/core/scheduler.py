from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings


scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    if scheduler.running:
        return

    from app.jobs.expire_orders import expire_orders_job
    from app.jobs.generate_instances import generate_instances_daily
    from app.jobs.sync_flight_status import sync_flight_status_job

    scheduler.add_job(
        expire_orders_job,
        trigger="interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="expire_orders",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        generate_instances_daily,
        trigger="cron",
        hour=settings.INSTANCE_GENERATION_HOUR,
        id="generate_instances",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        sync_flight_status_job,
        trigger="interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="sync_flight_status",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
