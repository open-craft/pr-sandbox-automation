"""
Set of funtions to orchestrate create/update/delete instance workflows
"""

import logging
from sqlmodel import select
from urllib.parse import urlparse
import yaml

from app.core.check_runs import (
    create_new_check_run,
    cancel_existing_pr_checkruns,
    update_checkrun,
    fetch_checkrun_pr,
    fetch_checkrun,
)
from app.core.sandbox import Sandbox, fetch_instance_list
from app.helpers.conf import config
from app.helpers.constants import (
    CheckRunStatus,
    SandboxStatus,
    MFE_CUSTOM_PORT,
    MFE_REPO_NAME_PREFIX,
    GithubActionTypes,
    WORKFLOW_SUCCESS_CONCLUSION,
    WORKFLOW_EXECUTION_ORDER,
    WorkflowType,
    ArgoCDSyncStatus,
    WorkFlowConclusion,
)
from app.helpers.db_utils import DBSession
from app.helpers.utils import get_secret
from app.helpers.exceptions import DBOperationException
from app.helpers.messages import (
    get_workflow_run_summary,
    get_argocd_run_summary,
    get_max_sandboxes_summary,
    get_generic_error_summary,
)
from app.helpers.utils import merge_dicts
from app.models.request_models import PullRequest, WorkflowRun
from app.models.sql_models import CheckRun, SandboxAudit, CancelledRun


logger = logging.getLogger(__name__)


def _post_generic_error_message(check_run: CheckRun, db_session: DBSession) -> None:
    summary = get_generic_error_summary()
    checkrun_status = CheckRunStatus.COMPLETE
    checkrun_conclusion = CheckRunStatus.FAILURE
    update_checkrun(
        check_run,
        summary,
        db_session,
        status=checkrun_status,
        conclusion=checkrun_conclusion,
    )


def _sandbox_audit_log(
    pull_request: PullRequest, sandbox_status: SandboxStatus, db_session: DBSession
) -> None:
    """
    Add an entry to DB when creating/deleting sandbox for audit purposes

    Args:
        pull_request (PullRequest): The object with PR details.
        db_session (DBSession): The DB session.
    """
    logger.debug("Logging sandbox %s %s", pull_request.sandbox_name, sandbox_status)
    sandbox_audit = SandboxAudit(
        repo=pull_request.repo_name,
        repo_html_url=pull_request.repo_html_url,
        pr_html_url=pull_request.html_url,
        fork_name=pull_request.fork_name,
        sandbox_name=pull_request.sandbox_name,
        sandbox_status=sandbox_status,
    )
    db_session.add_or_update(sandbox_audit)


def _update_instance(pull_request: PullRequest, sandbox: Sandbox) -> None:
    """
    Updates sandbox configs.

    Generates custom configs and trigger sandbox config update workflow.
    """
    logger.info("Updating sandbox %s", pull_request.sandbox_name)
    existing_sandbox_config = sandbox.tutor_config.content_as_dict

    instance_config = {
        "OPENEDX_COMMON_VERSION": pull_request.named_release.latest_common_version,
        "PICASSO_EXTRA_COMMANDS": pull_request.tutor_requirements,
        "GROVE_CREATE_DEMO_USER": True,
        "S3_STORAGE_BUCKET": existing_sandbox_config.get("STORAGE_BUCKET_NAME", ""),
        "S3_REGION": existing_sandbox_config.get("STORAGE_REGION", ""),
        "S3_HOST": urlparse(
            existing_sandbox_config.get("STORAGE_ENDPOINT_URL", "")
        ).hostname,
    }

    # Loads extra configs such as SMTP credentials which are not provided by the PHD stack yet
    extra_configs_from_secrets = yaml.safe_load(get_secret("pr-sandbox-extra-configs"))
    merge_dicts(instance_config, extra_configs_from_secrets)

    # Add custom MFE repo details for MFE PR
    if pull_request.repo_name.startswith(MFE_REPO_NAME_PREFIX):
        instance_config["GROVE_NEW_MFES"] = {
            pull_request.mfe_name: {
                "repository": pull_request.clone_url,
                "version": pull_request.branch_name,
                "port": MFE_CUSTOM_PORT,
            }
        }

    if settings := yaml.safe_load(pull_request.extra_settings):
        merge_dicts(instance_config, settings)

    sandbox.trigger_update(instance_config)


def _create_new_instance(
    pull_request: PullRequest, sandbox: Sandbox, db_session: DBSession
) -> None:
    """
    Creates a new sandbox instance.

    Triggers API calls to cluster's Github actions
    to trigger the create_instance workflow.

    Also records the event in DB for audit purposes.

    Args:
        pull_request (PullRequest): The object with PR details.
        db_session (DBSession): The DB session.
    """
    logger.info("Creating sandbox %s", pull_request.sandbox_name)
    is_mfe_pull_request = pull_request.repo_name.startswith(MFE_REPO_NAME_PREFIX)

    edx_platform_url = (
        config.default_platform_url if is_mfe_pull_request else pull_request.clone_url
    )

    edx_platform_branch = (
        pull_request.named_release.latest_common_version
        if is_mfe_pull_request
        else pull_request.branch_name
    )

    sandbox.trigger_create(
        edx_platform_url=edx_platform_url,
        edx_platform_branch=edx_platform_branch,
        tutor_version=pull_request.named_release.tutor_version,
    )

    _sandbox_audit_log(pull_request, SandboxStatus.CREATED, db_session)


def is_max_instances_exceeded() -> bool:
    """
    Check if the current active instance count has hit the upper limit.
    """
    instaces = fetch_instance_list()
    return len(instaces) >= config.max_sandbox_count


def create_or_update_instance(
    repository_url: str, head_sha: str, pull_request: PullRequest, db_session: DBSession
) -> None:
    """
    Create or Update an instance for the given pull request.

    Args:
        repository_url (str): The URL to be used to interact with check-runs
        head_sha (str): The head sha to refer to a check run instance
        pull_request (PullRequest): The pull request object
        db_session (DBSession): The DB Session
    """
    # Cancel any existing check runs for this sandbox before triggering a new one
    cancel_existing_pr_checkruns(repository_url, pull_request.sandbox_name, db_session)

    check_run = create_new_check_run(
        commit_sha=head_sha,
        repo_url=repository_url,
        sandbox_name=pull_request.sandbox_name,
        pr_url=pull_request.url,
        db_session=db_session,
    )

    try:
        sandbox = Sandbox(pull_request.sandbox_name)

        # Don't trigger any workflow if create instance workflow is already running
        if not sandbox.create_workflow_is_running():
            # If sandbox already exists update it, or create a new one
            if sandbox.exists:
                # Cancel any existing workflow runs for this sandbox first to avoid merge conflicts
                sandbox.cancel_any_existing_runs(db_session)
                _update_instance(pull_request, sandbox)
            elif is_max_instances_exceeded():
                logger.info(
                    "Sandbox %s cannot be created since max sandbox count exceeded",
                    sandbox.sandbox_name,
                )
                summary = get_max_sandboxes_summary()
                checkrun_status = CheckRunStatus.COMPLETE
                checkrun_conclusion = CheckRunStatus.FAILURE
                update_checkrun(
                    check_run,
                    summary,
                    db_session,
                    status=checkrun_status,
                    conclusion=checkrun_conclusion,
                )
            else:
                _create_new_instance(pull_request, sandbox, db_session)
    except Exception as e:
        _post_generic_error_message(check_run, db_session)
        raise e


def delete_instance(
    repository_url: str, pull_request: PullRequest, db_session: DBSession
) -> None:
    """
    Delete any existing instance for the given pull request

    Args:
        repository_url (str): The URL to be used to interact with check-runs
        pull_request (PullRequest): The pull request object
        db_session (DBSession): The DB Session
    """
    logger.info("Deleting sandbox %s", pull_request.sandbox_name)
    cancel_existing_pr_checkruns(repository_url, pull_request.sandbox_name, db_session)

    sandbox = Sandbox(pull_request.sandbox_name)
    # Cancel any existing workflow runs for this sandbox first to avoid merge conflicts
    sandbox.cancel_any_existing_runs(db_session)
    sandbox.trigger_delete()

    _sandbox_audit_log(pull_request, SandboxStatus.DESTROYED, db_session)


def fetch_pr_and_update_instance(
    check_suite_id: str,
    repository_url: str,
    head_sha: str,
    db_session: DBSession,
) -> None:
    """
    Fetches PR details for the check run and then triggers workflow
    run to update or create sandbox instance

    Args:
        check_suite_id (str): The check suite id linked with the check run
        repository_url (str): The URL to be used to interact with check-runs
        head_sha (str): The head sha to refer to a check run instance
        pull_request (PullRequest): The pull request object
        db_session (DBSession): The DB Session
    """
    check_run = fetch_checkrun(db_session, check_suite_id=check_suite_id)
    pull_request = fetch_checkrun_pr(check_run)
    create_or_update_instance(repository_url, head_sha, pull_request, db_session)


def post_checkrun_updates(
    check_run: CheckRun,
    sandbox: Sandbox,
    workflow_run: WorkflowRun,
    workflow_type: WorkflowType,
    db_session: DBSession,
    in_progress: bool = True,
    failed: bool = False,
    rerun: bool = False,
) -> None:
    """
    Post updates to checkruns based on workflow run status.
    """
    workflow_jobs = sandbox.fetch_run_jobs(workflow_run.jobs_url)
    summary = get_workflow_run_summary(
        workflow_jobs,
        workflow_type,
        db_session=db_session,
        conclusion=workflow_run.conclusion,
        attempt=workflow_run.attempt,
        in_progress=in_progress,
        failed=failed,
        rerun=rerun,
    )

    # Check run can only be in-progress or completed as failed.
    # Check run is never update as successful here since that status
    # is only updated once ArgoCD sync is completed successfully.
    checkrun_status = CheckRunStatus.IN_PROGRESS
    checkrun_conclusion = None
    if not in_progress and failed and not rerun:
        checkrun_status = CheckRunStatus.COMPLETE
        checkrun_conclusion = CheckRunStatus.FAILURE

    logger.debug(
        "Updating Checkrun for %s with status %s and conclusion %s",
        sandbox.sandbox_name,
        checkrun_status,
        checkrun_conclusion,
    )
    update_checkrun(
        check_run,
        summary,
        db_session,
        status=checkrun_status,
        conclusion=checkrun_conclusion,
    )


def trigger_next_workflow(
    workflow_type: WorkflowType,
    check_run: CheckRun,
    sandbox: Sandbox,
    db_session: DBSession,
) -> None:
    """
    Trigger the next workflow on successful completion of the last.
    """
    logger.debug("Current workflow %s, triggering next workflow", workflow_type)
    current_index = WORKFLOW_EXECUTION_ORDER.index(workflow_type)
    try:
        next_workflow = WORKFLOW_EXECUTION_ORDER[current_index + 1]
        match next_workflow:
            case WorkflowType.UPDATE_INSTANCE:
                pull_request = fetch_checkrun_pr(check_run)
                _update_instance(pull_request, sandbox)
            case WorkflowType.BUILD_ALL_IMAGES:
                sandbox.trigger_build()
    except IndexError:
        # If the last step of the workflow runs i.e. Build images,
        # is completed, then mark check_run build_complete status
        # as True in DB and wait for ArgoCD sync to start.
        if workflow_type == WorkflowType.BUILD_ALL_IMAGES:
            check_run.build_complete = True
            db_session.add_or_update(check_run)


def handle_workflow_run(
    github_action: GithubActionTypes,
    workflow_run: WorkflowRun,
    workflow_type: WorkflowType,
    db_session: DBSession,
) -> None:
    """
    Handle workflow run event notifications.
    """
    # Fetch the active checkrun for this sandbox if one exists
    try:
        check_run = fetch_checkrun(
            db_session,
            sandbox_name=workflow_run.sandbox_name,
            deployment_status=CheckRunStatus.IN_PROGRESS,
        )
        sandbox = Sandbox(workflow_run.sandbox_name)
    except DBOperationException:
        logger.info(
            "Active checkrun for sandbox %s not found", workflow_run.sandbox_name
        )
        return

    try:
        if github_action == GithubActionTypes.IN_PROGRESS:
            post_checkrun_updates(
                check_run, sandbox, workflow_run, workflow_type, db_session
            )
            return

        if workflow_run.conclusion in WORKFLOW_SUCCESS_CONCLUSION:
            trigger_next_workflow(workflow_type, check_run, sandbox, db_session)
            post_checkrun_updates(
                check_run,
                sandbox,
                workflow_run,
                workflow_type,
                db_session,
                in_progress=False,
            )
        elif workflow_run.conclusion == WorkFlowConclusion.CANCELLED:
            # Check if the workflow run cancellation was triggered
            # intentionally by this app. If so, ignore it. If not,
            # then update checkrun as failed.
            try:
                query = select(CancelledRun).where(
                    CancelledRun.run_id == workflow_run.id
                )
                db_session.fetch_one(query)
            except DBOperationException:
                post_checkrun_updates(
                    check_run,
                    sandbox,
                    workflow_run,
                    workflow_type,
                    db_session,
                    in_progress=False,
                    failed=True,
                )
        else:
            rerun = False
            # Handle failed workflow runs
            if workflow_run.attempt < config.max_run_attempt:
                rerun = True
                sandbox.trigger_workflow_rerun(workflow_run.id, workflow_run.rerun_url)

            post_checkrun_updates(
                check_run,
                sandbox,
                workflow_run,
                workflow_type,
                db_session,
                in_progress=False,
                failed=True,
                rerun=rerun,
            )
    except Exception as e:
        _post_generic_error_message(check_run, db_session)
        raise e


def handle_argocd(
    check_run: CheckRun,
    application_name: str,
    argocd_state: ArgoCDSyncStatus,
    db_session: DBSession,
) -> None:
    """
    Handle ArgoCD sync events notifications.
    """
    sandbox = Sandbox(check_run.sandbox_name)
    sandbox_config = sandbox.tutor_config.content_as_dict
    if argocd_state == ArgoCDSyncStatus.RUNNING:
        summary = get_argocd_run_summary(
            in_progress=True,
            failed=False,
            sandbox_config=sandbox_config,
            application_name=application_name,
        )
        checkrun_status = CheckRunStatus.IN_PROGRESS
        checkrun_conclusion = None
    elif argocd_state == ArgoCDSyncStatus.SUCCEEDED:
        summary = get_argocd_run_summary(
            in_progress=False,
            failed=False,
            sandbox_config=sandbox_config,
            application_name=application_name,
        )
        checkrun_status = CheckRunStatus.COMPLETE
        checkrun_conclusion = CheckRunStatus.SUCCESS
    else:
        summary = get_argocd_run_summary(
            in_progress=False,
            failed=True,
            sandbox_config=sandbox_config,
            application_name=application_name,
        )
        checkrun_status = CheckRunStatus.COMPLETE
        checkrun_conclusion = CheckRunStatus.FAILURE

    logger.debug(
        "Updating Checkrun for %s with status %s and conclusion %s",
        check_run.sandbox_name,
        checkrun_status,
        checkrun_conclusion,
    )

    update_checkrun(
        check_run,
        summary,
        db_session,
        status=checkrun_status,
        conclusion=checkrun_conclusion,
    )
