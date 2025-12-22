"""
Data models representing tables using SQLModel
"""

from datetime import datetime, timezone
from sqlmodel import Field, SQLModel
import uuid

from app.helpers.constants import CheckRunStatus, SandboxStatus


def utcnow():
    return datetime.now(timezone.utc)


class CheckRun(SQLModel, table=True):
    """
    Data model to track check runs
    """

    id: int = Field(primary_key=True)
    check_run_id: str = Field(index=True, unique=True)
    head_sha: str
    repo_url: str
    sandbox_name: str = Field(index=True)
    check_suite_id: str = Field(index=True)
    pr_url: str
    build_complete: bool = Field(default=False, index=True)
    deployment_status: CheckRunStatus = Field(index=True)


class WorkflowLogsLink(SQLModel, table=True):
    """
    Data model to map workflow job logs url to unique identifier
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    url: str


class SandboxAudit(SQLModel, table=True):
    """
    Data model to log sandbox activities
    """

    id: int = Field(primary_key=True)
    repo: str = Field(index=True)
    repo_html_url: str
    pr_html_url: str
    fork_name: str
    sandbox_name: str
    sandbox_status: SandboxStatus
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class CancelledRun(SQLModel, table=True):
    """
    Data model to track check runs which are cancelled
    """

    id: int = Field(primary_key=True)
    run_id: str = Field(index=True, unique=True)
