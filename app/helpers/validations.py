"""
Validation related functions
"""

from base64 import b64decode
from fastapi import Request, HTTPException
import hmac
import hashlib

from app.helpers.conf import config
from app.helpers.constants import (
    GithubActionTypes,
    GithubEventTypes,
    GITHUB_EVENT_ACTION_MAP,
    SIGNATURE_HEADER,
    SIGNATURE_PREFIX,
    AUTHORIZATION_HEADER,
    AUTHORIZATION_PREFIX,
    WorkflowType,
)
from app.helpers.exceptions import UnactionableRequestException
from app.helpers.utils import get_secret
from app.models.request_models import GithubWebhookRequest


async def validate_signature(request: Request):
    """
    Validate webhook request signature

    Args:
        request (Request): The request object

    Raises:
        UnactionableRequestException: If signature header missing or malformed
        HTTPException: If signature validation fails (status code 403)
    """
    if not (
        request_signature := request.headers.get(SIGNATURE_HEADER, None)
    ) or not request_signature.startswith(SIGNATURE_PREFIX):
        raise UnactionableRequestException(
            f"{SIGNATURE_HEADER} header missing or malformed"
        )

    payload = await request.body()
    request_signature = request_signature[len(SIGNATURE_PREFIX) :]

    expected_signature = hmac.new(
        get_secret("pr-sandbox-github-webhook-secret").encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, request_signature):
        raise HTTPException(
            status_code=403, detail="Request signature could not be validated"
        )


async def validate_auth(request: Request):
    """
    Validate the auth information in webhook request header

    Args:
        request (Request): The request object

    Raises:
        UnactionableRequestException: If auth header missing or malformed
        HTTPException: If auth validation fails (status code 403)
    """
    if not (
        request_authorization := request.headers.get(AUTHORIZATION_HEADER, None)
    ) or not request_authorization.startswith(AUTHORIZATION_PREFIX):
        raise UnactionableRequestException(
            f"{AUTHORIZATION_HEADER} header missing or malformed"
        )

    b64encoded_password = request_authorization[len(AUTHORIZATION_PREFIX) :]
    appened_password = b64decode(b64encoded_password).decode("utf8")
    auth_password = appened_password.split(":", 1)[-1]

    if auth_password != get_secret("pr-sandbox-argocd-webhook-auth"):
        raise HTTPException(
            status_code=403,
            detail="Request authorization details could not be validated",
        )


def _validate_request_actionable(
    github_event: GithubEventTypes, request: GithubWebhookRequest
):
    """
    Validate if the request is actionable.

    Checks if supported action is triggered for a given event
    Checks if pull_request events are paired with the correct PR label
    Checks if check_suite and check_run events have correct Github app identifier

    Args:
        github_event (GithubEventTypes): Github event type of the request
        request (GithubWebhookRequest): The request


    Raises:
        UnactionableRequestException: Raised with appropriate error details
                                        if validation fails.
    """
    pr_label = config.pr_label
    github_app_id = config.github_app_identifier

    # Verify if correct action is triggered for correct event
    if request.github_action not in GITHUB_EVENT_ACTION_MAP[github_event]:
        raise UnactionableRequestException(
            f"Invalid action '{request.github_action}' for event '{github_event}'"
        )

    # Verify pull_request events are paired with the correct PR label
    if github_event == GithubEventTypes.PULL_REQUEST:
        if request.github_action in [
            GithubActionTypes.LABELED,
            GithubActionTypes.UNLABELED,
        ]:
            if not request.action_label == pr_label:
                raise UnactionableRequestException(
                    f"Incorrect label for '{request.github_action}' action for '{github_event}' event"
                )
        elif pr_label not in request.pull_request.flat_labels:
            raise UnactionableRequestException(
                f"Incorrect label for '{request.github_action}' action for '{github_event}' event"
            )

    # Verify check run events have a check run id
    if github_event == GithubEventTypes.CHECK_RUN and not request.check_run_id:
        raise UnactionableRequestException(
            "check_run id is mandatory for check_run events"
        )

    # Verify check_run/check_suite events have correct Github app identifier
    if github_event in [GithubEventTypes.CHECK_RUN, GithubEventTypes.CHECK_SUITE]:
        if not request.app_id or request.app_id != github_app_id:
            raise UnactionableRequestException(
                f"Gitub app id missing or incorrect for '{github_event}' event"
            )

    # Verify workflow job is of a valid type and has a valid sandbox name
    if github_event == GithubEventTypes.WORKFLOW_RUN:
        if not request.workflow:
            raise UnactionableRequestException(
                f"Workflow type details missing for '{github_event}' event"
            )
        if request.workflow.type == WorkflowType.DELETE_INSTANCE:
            raise UnactionableRequestException(
                f"'{github_event}' event for {WorkflowType.DELETE_INSTANCE} workflows are ignored"
            )
        if not request.workflow_run.sandbox_name:
            raise UnactionableRequestException(
                f"A valid sandbox name is missing from '{github_event}' event"
            )


def validate_request(github_event: GithubEventTypes, request: GithubWebhookRequest):
    """
    Runs a number of validations on the request.

    Checks if installation id is valid and then passes
    the request object to _validate_request_actionable()
    function for additional validations

    Args:
        github_event (GithubEventTypes): Github event type of the request
        request (GithubWebhookRequest): The request

    Raises:
        UnactionableRequestException: Raised with appropriate error details
                                        if validation fails.
    """
    if request.installation_id != get_secret("pr-sandbox-pr-installation-id"):
        raise UnactionableRequestException("The provided installation id is invalid")

    _validate_request_actionable(github_event, request)
