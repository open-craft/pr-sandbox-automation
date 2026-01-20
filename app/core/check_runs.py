"""
Set of funtions to create/update/fetch/cancel checkruns
"""

import logging
from sqlmodel import select

from app.core.github import PRGithubClient
from app.helpers.constants import CHECK_RUN_NAME, CheckRunStatus
from app.helpers.db_utils import DBSession
from app.helpers.messages import get_cancelled_checkrun_summary
from app.helpers.utils import get_secret
from app.models.request_models import PullRequest
from app.models.sql_models import CheckRun


logger = logging.getLogger(__name__)

pr_github_client = PRGithubClient(get_secret("pr-sandbox-pr-installation-id"))


def create_new_check_run(
    commit_sha: str,
    repo_url: str,
    sandbox_name: str,
    pr_url: str,
    db_session: DBSession,
) -> CheckRun:
    """
    Creates a new check run and adds a new entry in DB.

    Args:
        commit_sha (str): Head sha of base branch
        repo_url (str): Target repo url
        sandbox_name (str): Name of the sandbox
        pr_url (str): PR URL
        db_session (DBSession): The DB session

    Returns:
        int: Check run ID
    """
    logger.debug("Creating a new check run for %s", sandbox_name)
    # API call to create a new check run
    create_response = pr_github_client.create_check_run(
        CHECK_RUN_NAME, commit_sha, repo_url
    )

    # Create a new entry in DB for the check run just created
    check_run = CheckRun(
        check_run_id=create_response["id"],
        head_sha=commit_sha,
        repo_url=repo_url,
        sandbox_name=sandbox_name,
        pr_url=pr_url,
        check_suite_id=create_response["check_suite"]["id"],
        deployment_status=CheckRunStatus.IN_PROGRESS,
    )
    db_session.add_or_update(check_run)

    return check_run


def update_checkrun(
    check_run: CheckRun,
    summary: str,
    db_session: DBSession,
    status: str = CheckRunStatus.IN_PROGRESS,
    conclusion: str | None = None,
):
    """
    Updates checkrun summary.

    Args:
        check_run (CheckRun): The check run to update
        summary (str): Summary to be updated to checkrun
        status (str, optional): Checkrun Status. Defaults to CheckRunStatus.IN_PROGRESS.
        conclusion (str | None, optional): Checkrun Conclusion. Defaults to None.
    """
    logger.debug(
        "Updating checkrun for %s with status %s", check_run.sandbox_name, status
    )
    # Update DB entry with completion status
    if conclusion:
        check_run.deployment_status = conclusion
        db_session.add_or_update(check_run)

    pr_github_client.update_check_run(
        check_run.check_run_id,
        status,
        summary,
        check_run.repo_url,
        conclusion=conclusion,
    )


def cancel_existing_pr_checkruns(
    repo_url: str, sandbox_name: str, db_session: DBSession
):
    """
    Cancels all in-progress check runs of the given sandbox.
    Also marks the check run DB entries as cancelled.

    Args:
        repo_url (str): URL of the PR repo
        sandbox_name (str): Name of the sandbox
        db_session (DBSession): The DB session
    """
    logger.debug("Cancelling existing checkruns for %s", sandbox_name)
    # Fetch all in-progress checkruns for the given sandbox
    fetch_active_check_run_stmt = select(CheckRun).where(
        CheckRun.sandbox_name == sandbox_name,
        CheckRun.deployment_status == CheckRunStatus.IN_PROGRESS,
    )
    check_runs: list[CheckRun] = db_session.fetch_all(fetch_active_check_run_stmt)

    # Mark the check runs as cancelled
    for check_run in check_runs:
        # Fetch existing summary posted in the checkrun, so we can append to it
        checkrun_summary = pr_github_client.fetch_check_run_summary(
            check_run.check_run_id, repo_url
        )
        update_checkrun(
            check_run,
            get_cancelled_checkrun_summary(checkrun_summary),
            db_session,
            status=CheckRunStatus.COMPLETE,
            conclusion=CheckRunStatus.CANCELLED,
        )


def fetch_checkrun(
    db_session: DBSession,
    check_suite_id: str | None = None,
    sandbox_name: str | None = None,
    deployment_status: str | None = None,
    build_complete: bool = False,
) -> CheckRun:
    """
    Fetches a matching checkrun from DB

    Args:
        db_session (DBSession): The DB Session
        check_suite_id (str | None, optional): Checksuite ID. Defaults to None.
        sandbox_name (str | None, optional): Name of the sandbox. Defaults to None.
        deployment_status (str | None, optional): Deplomyent Status of the Sandbox. Defaults to None.
        build_complete (bool, optional): Flag to mark that build is complete fo checkrun. Defaults to False.

    Returns:
        CheckRun: The fetched check run object
    """
    logger.debug(
        "Fetching checkrun with check_suite_id %s, sandbox_name %s, deployment_status %s, build_complete %s",
        check_suite_id,
        sandbox_name,
        deployment_status,
        build_complete,
    )
    query = select(CheckRun)

    if check_suite_id:
        query = query.where(CheckRun.check_suite_id == check_suite_id)
    if sandbox_name:
        query = query.where(CheckRun.sandbox_name == sandbox_name)
    if deployment_status:
        query = query.where(CheckRun.deployment_status == deployment_status)
    if build_complete:
        query = query.where(CheckRun.build_complete == build_complete)

    return db_session.fetch_one(query)


def fetch_checkrun_pr(check_run: CheckRun) -> PullRequest:
    """
    Fetches the details of the PR associated with a checkrun.

    Args:
        check_run (CheckRun): The checkrun object for which the PR details is to be fetched.
        db_session (DBSession): The DB Session

    Returns:
        PullRequest: The pull request object
    """
    logger.debug("Fetching PR details for %s", check_run.sandbox_name)
    return pr_github_client.fetch_pull_request(check_run.pr_url)
