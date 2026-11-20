"""Streamlit page components for Athena."""

from .dashboard import dashboard_page
from .tasks import tasks_page
from .schedule import schedule_page
from .memory import memory_page
from .projects import projects_page
from .project_detail import project_detail_page
from .reports import reports_page
from .export import export_page
from .settings import settings_page

__all__ = [
    "dashboard_page",
    "tasks_page",
    "schedule_page",
    "memory_page",
    "projects_page",
    "project_detail_page",
    "reports_page",
    "export_page",
    "settings_page",
]
