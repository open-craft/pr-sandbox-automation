from app.helpers.conf import config
from app.helpers.constants import (
    WORKFLOW_EXECUTION_ORDER,
    WORKFLOW_HEADERS,
    WorkFlowStatus,
    WorkflowType,
    WorkFlowConclusion,
)
from app.helpers.db_utils import DBSession
from app.models.request_models import WorkflowJob
from app.models.sql_models import WorkflowLogsLink


INDENT = "&nbsp;&nbsp;&nbsp;&nbsp;"


def get_cancelled_checkrun_summary(existing_summary: str) -> str:
    """
    Generate summary for cancelled checkrun

    Args:
        existing_summary (str): Existing summary to append to.
    """
    return f"{existing_summary}\n\n### 🚫 Sandbox Deployment has been cancelled"


def _status_tag(in_progress: bool, conclusion: str | None) -> str:
    if in_progress:
        return "Running"
    return conclusion.capitalize()


def _check_job_in_progress(status: str) -> bool:
    return status != WorkFlowStatus.COMPLETE


def _get_run_status_emoji(in_progress: bool, conclusion: str | None) -> str:
    if in_progress:
        return "🛠️"

    if conclusion == WorkFlowConclusion.SUCCESS:
        return "✅"

    return "❌"


def _get_job_status_emoji(in_progress: bool, conclusion: str | None):
    if in_progress:
        return "🔧"

    if conclusion == WorkFlowConclusion.SUCCESS:
        return "🟢"

    if conclusion in [WorkFlowConclusion.NEUTRAL, WorkFlowConclusion.SKIPPED]:
        return "⏭️"

    if conclusion == WorkFlowConclusion.CANCELLED:
        return "🚫"

    return "🔴"


def _append_logs_link(
    summary: str, job: WorkflowJob, in_progress: bool, db_session: DBSession
):
    if not in_progress and job.conclusion == WorkFlowConclusion.FAILURE:
        workflow_logs_link = WorkflowLogsLink(url=job.logs_url)
        db_session.add_or_update(workflow_logs_link)
        return (
            summary
            + f"\n{INDENT}{INDENT}*Failure log: {config.app_logs_url}/{workflow_logs_link.id}*\n"
        )
    return summary


def _next_steps_message(is_first_step: bool = False) -> str:
    return f"\n\n### ⏳⏳ *Waiting for status of {'first' if is_first_step else 'next'} steps*"


def get_starting_message() -> str:
    return _next_steps_message(is_first_step=True)


def get_workflow_run_summary(
    workflow_jobs: list[WorkflowJob],
    workflow_type: WorkflowType,
    db_session: DBSession | None = None,
    conclusion: str | None = None,
    in_progress: bool = False,
    failed: bool = False,
) -> str:
    """
    Generate summary for workflow run events.

    Args:
        workflow_jobs (list[WorkflowJob]): List of jobs in the workflow run
        workflow_type (WorkflowType): Type of the workflow run
        conclusion (str | None, optional): Conclusion if any. Defaults to None.
        in_progress (bool, optional): If workflow is still in progress. Defaults to False.
        failed (bool, optional): If workflow failed. Defaults to False.

    Returns:
        str: The generated summary
    """
    summary = ""
    for workflow in WORKFLOW_EXECUTION_ORDER:
        # Going down the execution order, assuming all
        # workflows above the current workflow type have
        # completed successfully.
        if workflow != workflow_type:
            summary += f"\n### {_get_run_status_emoji(False, WorkFlowConclusion.SUCCESS)} {WORKFLOW_HEADERS[workflow]}\n\n"
        else:
            summary += f"\n### {_get_run_status_emoji(in_progress, conclusion)} {WORKFLOW_HEADERS[workflow_type]}\n"
            # Update the status of individual jobs of the workflow run in progress
            for job in workflow_jobs:
                job_in_progress = _check_job_in_progress(job.status)
                summary += f"\n{INDENT}{_get_job_status_emoji(job_in_progress, job.conclusion)} **{job.workflow_job_type} job** - *{_status_tag(job_in_progress, job.conclusion)}*"
                summary = _append_logs_link(summary, job, job_in_progress, db_session)
            # If current workflow is completed successfully, then append status
            # saying that we are waiting for the next workflow to start. This is required as
            # sometimes there might be a delay between the last workflow run completing
            # and the next starting up. We don't want the user to think that the sandbox
            # is fully deployed, based on the successful status of the last workflow run.
            if not in_progress and not failed:
                summary += _next_steps_message()
            break
    return summary


def get_argocd_run_summary(
    in_progress: bool, failed: bool, sandbox_config: dict, application_name: str
) -> str:
    # Assuming all workflow runs are completed successful before
    # we got to updating the sync status of ArgoCD.
    summary = get_workflow_run_summary(
        [],
        WorkflowType.DELETE_INSTANCE,
        conclusion="",
        in_progress=False,
        failed=False,
    )
    summary += f"\n### {_get_run_status_emoji(in_progress, WorkFlowConclusion.FAILURE if failed else WorkFlowConclusion.SUCCESS)} ArgoCD Sync"
    summary += f"\n{INDENT} **Go to [ArgoCD UI]({config.argocd_app_url}/{application_name}) to check the sync status and to access pod logs and pod shell**"
    if not in_progress and not failed:
        summary += "\n\n### 🚀 Deployment Completed Successfully"
        summary += "\n\nSandbox Links:"
        summary += f"\n{INDENT}🎓 [LMS](https://{sandbox_config['LMS_HOST']})"
        summary += f"\n{INDENT}📝 [Studio](https://{sandbox_config['CMS_HOST']})"

    return summary


def get_max_sandboxes_summary() -> str:
    """
    Generate summary for sandbox cancelled due to max sandboxes
    """
    return "\n\n### 🚫 Sandbox deployment has been cancelled since the maximum number of sandboxes are already deployed"
