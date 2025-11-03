from app.helpers.constants import (
    CHECKRUN_CANCELLED_MESSAGE,
    WORKFLOW_EXECUTION_ORDER,
    WORKFLOW_HEADERS,
    WorkFlowStatus,
    WorkflowType,
)
from app.models.request_models import WorkflowJob


def get_cancelled_checkrun_summary(existing_summary: str) -> str:
    """
    Generate summary for canceller checkrun

    Args:
        existing_summary (str): Existing summary to append to.
    """
    return f"{existing_summary}\n\n### {CHECKRUN_CANCELLED_MESSAGE}"


def _status_tag(in_progress: bool, conclusion: str | None) -> str:
    if in_progress:
        return "Running"
    return conclusion.capitalize()


def _check_job_in_progress(status: str) -> bool:
    return status != WorkFlowStatus.COMPLETE


def get_workflow_run_summary(
    workflow_jobs: list[WorkflowJob],
    workflow_type: WorkflowType,
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
            summary += f"\n### {WORKFLOW_HEADERS[workflow]} - Success\n\n"
        else:
            summary += f"\n### {WORKFLOW_HEADERS[workflow_type]} - {_status_tag(in_progress, conclusion)}\n"
            # Update the status of individual jobs of the workflow run in progress
            for job in workflow_jobs:
                job_in_progress = _check_job_in_progress(job.status)
                summary += f"\n{job.workflow_job_type} - {_status_tag(job_in_progress, job.conclusion)}"
            # If current workflow is completed successfully, then append status
            # saying that we are waiting for the next workflow to start. This is required as
            # sometimes there might be a delay between the last workflow run completing
            # and the next starting up. We don't want the user to think that the sandbox
            # is fully deployed, based on the successful status of the last workflow run.
            if not in_progress and not failed:
                summary += "\n### Waiting for status of next steps"
            break
    return summary


def get_argocd_run_summary(in_progress: bool, failed: bool) -> str:
    # Assuming all workflow runs are completed successful before
    # we got to updating the sync status of ArgoCD.
    summary = get_workflow_run_summary(
        [],
        WorkflowType.DELETE_INSTANCE,
        conclusion="",
        in_progress=False,
        failed=False,
    )
    summary += "\n### ArgoCD Sync - "
    if in_progress:
        summary += "Running"
    elif failed:
        summary += "Failed"
    else:
        summary += "Success\n\n### Deployment Completed Successfully"

    return summary
