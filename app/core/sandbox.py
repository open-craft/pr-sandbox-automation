"""
This module provides the Sandbox class with a set of methods to trigger and fetch workflow jobs and runs
"""

import json
import logging
import uuid
from sqlmodel import select

from app.core.github import ClusterGithubClient
from app.helpers.constants import (
    WorkflowType,
    WORKFLOW_ACTIVE,
)
from app.helpers.db_utils import DBSession
from app.helpers.exceptions import ClusterWorkflowNotFoundException
from app.helpers.utils import get_secret
from app.models.request_models import Workflow, WorkflowJob, GithubFile
from app.models.sql_models import CancelledRun, WorkflowLogsLink

logger = logging.getLogger(__name__)

cluster_github_client = ClusterGithubClient(
    get_secret("pr-sandbox-cluster-installation-id")
)


def fetch_job_logs(job_uuid: uuid.UUID, db_session: DBSession) -> str:
    """
    Fetches job log for the given job uuid.

    Args:
        db_session (DBSession): The DB Session
        uuid (str): UUID correspondinvg to the job log

    Returns:
        str: Job logs
    """
    logger.debug("Fetching workflow job log with uuid %s", job_uuid)
    query = select(WorkflowLogsLink).where(WorkflowLogsLink.id == job_uuid)
    logs_link: WorkflowLogsLink = db_session.fetch_one(query)
    return cluster_github_client.fetch_job_logs(logs_link.url)


class Sandbox:
    def __init__(self, sandbox_name: str):
        self.sandbox_name = sandbox_name
        self.workflows = cluster_github_client.get_workflow_list()
        self.in_progress_workflow_runs = None

    @property
    def tutor_config(self) -> GithubFile | None:
        return cluster_github_client.get_instance_config(self.sandbox_name)

    @property
    def exists(self) -> bool:
        """
        Checks if the sandbox exists in cluster.
        """
        return self.tutor_config is not None

    def _get_workflow(self, workflow_type: WorkflowType) -> Workflow:
        """
        Fetch the workflow of the given type.

        Args:
            type (WorkflowType): The workflow type

        Returns:
            Workflow: Object with details of the matching workflow

        Raises:
            ClusterWorkflowNotFoundException: No active workflow of given type is found
        """
        for workflow in self.workflows:
            if workflow.type == workflow_type and workflow.state == WORKFLOW_ACTIVE:
                return workflow

        logger.warning("Workflow type %s does not exist or not active", type)
        raise ClusterWorkflowNotFoundException(
            f"Active workflow with name {WorkflowType.UPDATE_INSTANCE} not found in cluster"
        )

    def trigger_update(self, new_config: dict) -> None:
        """
        Triggers update instance workflow.

        Args:
            new_config (dict): The config which will be merged with the instance's existing config.
        """
        logger.debug("Triggering update workflow for %s", self.sandbox_name)
        workflow = self._get_workflow(WorkflowType.UPDATE_INSTANCE)

        cluster_github_client.trigger_workflow_run(
            workflow.url,
            {
                "INSTANCE_NAME": self.sandbox_name,
                "CONFIG": json.dumps(new_config).replace('"', '\\"'),
            },
        )

    def trigger_create(
        self,
        edx_platform_url: str,
        edx_platform_branch: str,
        tutor_version: str,
    ) -> None:
        """
        Triggers create instance workflow.

        Args:
            edx_platform_url (str): edx-platform url to be used for the sandbox
            edx_platform_branch (str): edx-platform branch to be used for the sandbox
            tutor_version (str): tutor version to be used for the sandbox
        """
        logger.debug("Triggering create instance workflow for %s", self.sandbox_name)
        workflow = self._get_workflow(WorkflowType.CREATE_INSTANCE)

        cluster_github_client.trigger_workflow_run(
            workflow.url,
            {
                "INSTANCE_NAME": self.sandbox_name,
                "PLATFORM_NAME": self.sandbox_name,
                "EDX_PLATFORM_REPOSITORY": edx_platform_url,
                "EDX_PLATFORM_VERSION": edx_platform_branch,
                "TUTOR_VERSION": tutor_version,
            },
        )

    def trigger_delete(self) -> None:
        """
        Triggers delete instance workflow.
        """
        logger.debug("Triggering delete instance workflow for %s", self.sandbox_name)
        workflow = self._get_workflow(WorkflowType.DELETE_INSTANCE)

        cluster_github_client.trigger_workflow_run(
            workflow.url,
            {
                "INSTANCE_NAME": self.sandbox_name,
            },
        )

    def trigger_build(self) -> None:
        """
        Triggers build all images workflow.
        """
        logger.info("Triggering build workflow for %s", self.sandbox_name)
        workflow = self._get_workflow(WorkflowType.BUILD_ALL_IMAGES)

        cluster_github_client.trigger_workflow_run(
            workflow.url,
            {
                "INSTANCE_NAME": self.sandbox_name,
            },
        )

    def create_workflow_is_running(self) -> bool:
        """
        Checks if a create instance workflow is already running for this sandbox.

        Returns:
            bool: True to indicate create instance worflow is running.
        """
        logger.debug(
            "Checking if create instance workflow is already running for %s",
            self.sandbox_name,
        )
        workflow = self._get_workflow(WorkflowType.CREATE_INSTANCE)

        # Fetching a list of all workflow runs in progress currently
        if not self.in_progress_workflow_runs:
            self.in_progress_workflow_runs = (
                cluster_github_client.fetch_in_progress_workflow_runs()
            )

        for workflow_run in self.in_progress_workflow_runs:
            if (
                workflow_run.workflow_id == workflow.id
                and workflow_run.sandbox_name == self.sandbox_name
            ):
                return True
        return False

    def cancel_any_existing_runs(self, db_session: DBSession):
        """
        Cancels any existing workflow run for this sandbox
        """
        logger.debug("Cancelling any running workflow for %s", self.sandbox_name)

        # Fetching a list of all workflow runs in progress currently
        if not self.in_progress_workflow_runs:
            self.in_progress_workflow_runs = (
                cluster_github_client.fetch_in_progress_workflow_runs()
            )
        for workflow_run in self.in_progress_workflow_runs:
            if workflow_run.sandbox_name == self.sandbox_name:
                cluster_github_client._post_request(url=workflow_run.cancel_url)
                cancelled_runs = CancelledRun(run_id=workflow_run.id)
                db_session.add_or_update(cancelled_runs)

    def fetch_run_jobs(self, jobs_url: str) -> list[WorkflowJob]:
        """
        Fetchs a list of workflow jobs
        """
        return cluster_github_client.fetch_jobs(jobs_url)
