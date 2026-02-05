"""
Handler for Webhook Requests
"""

import logging
from fastapi import Depends, APIRouter, Header, BackgroundTasks
from fastapi.responses import PlainTextResponse
from redis import Redis
from typing import Annotated
import uuid

from app.core.check_runs import fetch_checkrun
from app.core.sandbox import fetch_job_logs
from app.core.webhook_actions import (
    create_or_update_instance,
    delete_instance,
    fetch_pr_and_update_instance,
    handle_workflow_run,
    handle_argocd,
)
from app.helpers.constants import GithubActionTypes, GithubEventTypes, CheckRunStatus
from app.helpers.db_utils import SessionDep
from app.helpers.exceptions import ActiveCheckrunNotFoundException, DBOperationException
from app.helpers.utils import get_secret
from app.helpers.validations import validate_signature, validate_request, validate_auth, validate_request_not_duplicate
from app.models.request_models import (
    GithubWebhookRequest,
    GithubWebhookHeader,
    ArgoWebhookRequest,
)

redis_client = Redis.from_url(get_secret("pr-sandbox-redis-connection-string"))
logger = logging.getLogger(__name__)

github_webhook_router = APIRouter(
    prefix="/github-webhook",
    tags=["webhook"],
    dependencies=[Depends(validate_signature)],
    responses={403: {"description": "Request signature could not be validated"}},
)

argocd_webhook_router = APIRouter(
    prefix="/argocd-webhook",
    tags=["webhook"],
    dependencies=[Depends(validate_auth)],
    responses={
        403: {"description": "Request authorization details could not be validated"}
    },
)

web_router = APIRouter(
    prefix="/web",
    tags=["web"],
)

system_router = APIRouter(
    prefix="/system",
    tags=["system"],
)


def handle_github_webhook(
    github_event: GithubEventTypes,
    request: GithubWebhookRequest,
    db_session: SessionDep,
    background_tasks: BackgroundTasks,
):
    """
    Trigger appropriate action based on the github event.

    Args:
        github_event (GithubEventTypes): The Github event which triggered the webhook request.
        request (GithubWebhookRequest): The webhook request.
        db_session (SessionDep): DB Session specific to each request.
        background_tasks (BackgroundTasks): BackgroundTasks object to run follow-actions for webhook requests.
    """
    match github_event, request.github_action:
        case GithubEventTypes.PULL_REQUEST, GithubActionTypes.SYNCHRONIZE:
            logger.info(
                "Handling %s github event for %s action for sandbox %s",
                github_event,
                request.github_action,
                request.pull_request.sandbox_name,
            )
            background_tasks.add_task(
                create_or_update_instance,
                request.repository_url,
                request.head_sha,
                request.pull_request,
                db_session,
            )
        case GithubEventTypes.PULL_REQUEST, GithubActionTypes.CLOSED:
            logger.info(
                "Handling %s github event for %s action for sandbox %s",
                github_event,
                request.github_action,
                request.pull_request.sandbox_name,
            )
            background_tasks.add_task(
                delete_instance,
                request.repository_url,
                request.pull_request,
                db_session,
            )
        case GithubEventTypes.PULL_REQUEST, GithubActionTypes.REOPENED:
            logger.info(
                "Handling %s github event for %s action for sandbox %s",
                github_event,
                request.github_action,
                request.pull_request.sandbox_name,
            )
            background_tasks.add_task(
                create_or_update_instance,
                request.repository_url,
                request.head_sha,
                request.pull_request,
                db_session,
            )
        case GithubEventTypes.PULL_REQUEST, GithubActionTypes.LABELED:
            logger.info(
                "Handling %s github event for %s action for sandbox %s",
                github_event,
                request.github_action,
                request.pull_request.sandbox_name,
            )
            background_tasks.add_task(
                create_or_update_instance,
                request.repository_url,
                request.head_sha,
                request.pull_request,
                db_session,
            )
        case GithubEventTypes.PULL_REQUEST, GithubActionTypes.UNLABELED:
            logger.info(
                "Handling %s github event for %s action for sandbox %s",
                github_event,
                request.github_action,
                request.pull_request.sandbox_name,
            )
            background_tasks.add_task(
                delete_instance,
                request.repository_url,
                request.pull_request,
                db_session,
            )
        case GithubEventTypes.CHECK_RUN | GithubEventTypes.CHECK_SUITE, _:
            logger.info(
                "Handling %s github event for %s action",
                github_event,
                request.github_action,
            )
            background_tasks.add_task(
                fetch_pr_and_update_instance,
                request.check_suite_id,
                request.repository_url,
                request.head_sha,
                db_session,
            )
        case GithubEventTypes.WORKFLOW_RUN, _:
            logger.info(
                "Handling %s github event for %s action for sandbox %s",
                github_event,
                request.github_action,
                request.workflow_run.sandbox_name,
            )
            background_tasks.add_task(
                handle_workflow_run,
                request.github_action,
                request.workflow_run,
                request.workflow.type,
                db_session,
            )


@github_webhook_router.post("/")
def github_handler(
    request: GithubWebhookRequest,
    headers: Annotated[GithubWebhookHeader, Header()],
    db_session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Github Webhook event handler
    """
    logger.info(headers)
    github_event = headers.x_github_event
    validate_request_not_duplicate(headers.x_hub_signature_256, redis_client)
    validate_request(github_event, request)
    handle_github_webhook(github_event, request, db_session, background_tasks)
    return {
        "event": github_event,
        "action": request.github_action,
    }


@argocd_webhook_router.post("/")
def argo_handler(
    request: ArgoWebhookRequest,
    db_session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    ArgoCD Webhook event handler
    """
    try:
        check_run = fetch_checkrun(
            db_session,
            sandbox_name=request.sandbox_name,
            deployment_status=CheckRunStatus.IN_PROGRESS,
            build_complete=True,
        )
    except DBOperationException:
        raise ActiveCheckrunNotFoundException(
            f"No active check run awaiting ArgoCD sync found for sandbox {request.sandbox_name}"
        )
    logger.info(
        "Handling ArgoCD event for sandbox %s - Sync status %s",
        request.sandbox_name,
        request.state,
    )
    background_tasks.add_task(
        handle_argocd, check_run, request.application, request.state, db_session
    )
    return {
        "event": "ArgoCD Sync",
    }


@web_router.get("/logs/{job_uuid}", response_class=PlainTextResponse)
def web_handler(
    job_uuid: uuid.UUID,
    db_session: SessionDep,
) -> str:
    """
    Handler for get job logs request
    """
    logger.info("Received request to fetch logs for job with UUID %s", job_uuid)
    try:
        return fetch_job_logs(job_uuid, db_session)
    except DBOperationException:
        raise ActiveCheckrunNotFoundException(
            f"No matching job log url found for UUID {job_uuid}"
        )


@system_router.get("/healthz")
def system_healthz() -> dict:
    """
    Health check for the system
    """
    return {"status": "ok"}
