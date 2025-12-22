"""
GitHub module provides clients for interacting with the GitHub API.

The GitHub API is used to retrieve information about pull requests, create
and update check runs, trigger workflows and fetch workflow logs.
"""

from datetime import datetime, timedelta, timezone
import jwt
import logging
import requests
from requests.models import Response

from app.helpers.conf import config
from app.helpers.constants import WorkFlowStatus
from app.helpers.exceptions import ObjectDoesNotExist, RateLimitExceeded
from app.helpers.utils import get_secret, merge_dicts
from app.models.request_models import (
    Workflow,
    GithubFile,
    WorkflowRun,
    WorkflowJob,
    PullRequest,
)


logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Client for interacting with the GitHub API.
    """

    def __init__(self, token: str) -> None:
        self.token = token

    @property
    def api_params(self) -> dict:
        return {
            "timeout": 30,
            "headers": {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": config.user_agent,
                "Time-Zone": "UTC",
            },
        }

    def _check_response_code(self, resp: Response, url: str) -> dict:
        """
        Check the status code of response and raise approprate error codes.
        Raises ObjectDoesNotExist if Github returns a 404 response.
        Raises RateLimitExceeded if Github return 403 response with
        X-RateLimit-Remaining header set to 0.
        """

        if resp.status_code == 404:
            raise ObjectDoesNotExist(f"404 response from {url}")

        remaining_requests = resp.headers.get("X-RateLimit-Remaining")
        if (
            resp.status_code == 403 or resp.status_code == 429
        ) and remaining_requests == "0":
            raise RateLimitExceeded(f"Rate limit exceeded when querying {url}")

        resp.raise_for_status()

        try:
            resp_data = resp.json()
        except requests.JSONDecodeError:
            if resp.text:
                logging.error("Unparsable response from url %s : %s", url, resp.text)
            resp_data = None
        return resp_data

    def _get_object(self, url: str, custom_params: dict = {}) -> dict:
        """
        Send a GET request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.
        """
        merge_dicts(custom_params, self.api_params)
        resp = requests.get(url, **custom_params)
        return self._check_response_code(resp, url)

    def _post_request(
        self, url: str, data: dict = None, custom_params: dict = {}
    ) -> dict:
        """
        Send a POST request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.
        """
        merge_dicts(custom_params, self.api_params)
        resp = requests.post(url, json=data, **custom_params)
        return self._check_response_code(resp, url)

    def _patch_request(
        self, url: str, data: dict = None, custom_params: dict = {}
    ) -> dict:
        """
        Send a PATCH request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.
        """
        merge_dicts(custom_params, self.api_params)
        resp = requests.patch(url, json=data, **custom_params)
        return self._check_response_code(resp, url)

    def fetch_app_installation_access_token(self, installation_id: str) -> dict:
        """
        Fetch a new installation access token from Github.

        Args:
            installation_id (str): The Github app installation ID

        Returns:
            dict: Response as dict
        """

        return self._post_request(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        )


class GithubAccessToken:
    """
    Utility class representing an access token
    """

    def __init__(self, installation_id: str) -> None:
        self.installation_id = installation_id
        self._access_token = None
        self._expires_at = datetime.now(timezone.utc)

    def _construct_jwt(self) -> str:
        """
        Constructs a jwt token
        """
        github_private_key = get_secret("pr-sandbox-github-private-key")
        payload = {
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "iss": config.github_app_identifier,
        }

        return jwt.encode(payload, github_private_key, algorithm="RS256")

    def _is_expired(self) -> bool:
        """
        Check if access token is expired.
        """
        return datetime.now(timezone.utc) > self._expires_at

    def _fetch_access_token(self) -> None:
        """
        Fetches access token from Github
        """
        github_client = GitHubClient(self._construct_jwt())
        github_response = github_client.fetch_app_installation_access_token(
            self.installation_id
        )

        self._access_token = github_response["token"]
        self._expires_at = datetime.fromisoformat(github_response["expires_at"])

    def get_access_token(self) -> str:
        """
        Returns an access_token if present otherwise fetches a new one.

        Also fetches a new token if the current token is expired.
        """
        if not self._access_token or self._is_expired():
            self._fetch_access_token()
        return self._access_token


class PRGithubClient(GitHubClient):
    """
    Github Client for PR related API calls.
    """

    def __init__(self, installation_id: str) -> None:
        self.pr_access_token = GithubAccessToken(installation_id)
        super().__init__(self.pr_access_token.get_access_token())

    def _get_object(self, url: str, custom_params: dict = {}) -> dict:
        """
        Send a GET request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.

        The method also ensures a valid access token is uesd for the request
        for PR API calls.
        """
        self.token = self.pr_access_token.get_access_token()
        return super()._get_object(url, custom_params=custom_params)

    def _post_request(
        self, url: str, data: dict = None, custom_params: dict = {}
    ) -> dict:
        """
        Send a POST request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.

        The method also ensures a valid access token is uesd for the request
        for PR API calls.
        """
        self.token = self.pr_access_token.get_access_token()
        return super()._post_request(url, data, custom_params=custom_params)

    def _patch_request(
        self, url: str, data: dict = None, custom_params: dict = {}
    ) -> dict:
        """
        Send a PATCH request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.

        The method also ensures a valid access token is uesd for the request
        for PR API calls.
        """
        self.token = self.pr_access_token.get_access_token()
        return super()._patch_request(url, data, custom_params=custom_params)

    def create_check_run(self, name: str, head_sha: str, repo_url: str) -> dict:
        """
        Create a new check run for a commit.

        Args:
            name (str): Name of the new check run
            head_sha (str): The sha of the base head commit of the PR
            repo_url (str): The API url of the target repo
        """

        return self._post_request(
            f"{repo_url}/check-runs",
            {
                "name": name,
                "head_sha": head_sha,
            },
        )

    def update_check_run(
        self,
        check_run_id: str,
        status: str,
        summary: str,
        repo_url: str,
        conclusion: str | None = None,
    ) -> dict:
        """
        Updates the status and summary of a checkrun

        Args:
            check_run_id (str): ID of checkrun to update
            status (str): Status to post
            summary (str): Summary to post
            repo_url (str): Checkrun repo url
            conclusion (str | None, optional): Conclusion to post. Defaults to None.
        """
        data = {
            "status": status,
            "output": {"title": "Sandbox Deployment", "summary": summary},
        }

        if conclusion:
            data["conclusion"] = conclusion

        return self._patch_request(f"{repo_url}/check-runs/{check_run_id}", data)

    def fetch_check_run_summary(
        self,
        check_run_id: str,
        repo_url: str,
    ) -> str:
        """
        Fetches existing summary of a checkrun

        Args:
            check_run_id (str): The ID of the checkrun
            repo_url (str): The repository URL

        Returns:
            str: The summary of the checkrun
        """
        resp = self._get_object(f"{repo_url}/check-runs/{check_run_id}")
        return resp["output"]["summary"]

    def fetch_pull_request(self, pr_url: str) -> PullRequest:
        """
        Fetch details of pull request using given URL

        Args:
            pr_url (str): URL of the PR

        Returns:
            PullRequest: The PR object
        """
        resp = self._get_object(pr_url)
        return PullRequest.model_validate(resp)


class ClusterGithubClient(GitHubClient):
    """
    Github Client for PR related API calls.
    """

    def __init__(self, installation_id: str) -> None:
        self.cluster_access_token = GithubAccessToken(installation_id)
        self.repo_url = config.cluster_github_repo_url
        super().__init__(self.cluster_access_token.get_access_token())

    def _get_object(
        self, url: str = None, path: str = "", custom_params: dict = {}
    ) -> dict:
        """
        Send a GET request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.

        The method also ensures a valid access token is uesd for the request
        for Cluster API calls.
        """
        self.token = self.cluster_access_token.get_access_token()
        api_url = url if url else f"{self.repo_url}{path}"
        return super()._get_object(api_url, custom_params=custom_params)

    def _post_request(
        self,
        url: str = None,
        path: str = "",
        data: dict = None,
        custom_params: dict = {},
    ) -> dict:
        """
        Send a POST request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.

        The method also ensures a valid access token is uesd for the request
        for Cluster API calls.
        """
        self.token = self.cluster_access_token.get_access_token()
        api_url = url if url else f"{self.repo_url}{path}"
        return super()._post_request(api_url, data, custom_params=custom_params)

    def _patch_request(
        self, url: str, data: dict = None, custom_params: dict = {}
    ) -> dict:
        """
        Send a PATCH request to the provided URL, attaching custom params, and
        returns the deserialized object from the returned JSON.

        The method also ensures a valid access token is uesd for the request
        for Cluster API calls.
        """
        self.token = self.cluster_access_token.get_access_token()
        return super()._patch_request(url, data, custom_params=custom_params)

    def get_instance_config(self, instance_name: str) -> GithubFile | None:
        """
        Returns the instance config from the PHD cluster repository.
        """
        try:
            file_info = self._get_object(
                path=f"/contents/instances/{instance_name}/config.yml?ref=main",
                custom_params={
                    "headers": {
                        "Accept": "application/vnd.github.object+json",
                    }
                },
            )
        except ObjectDoesNotExist:
            return None

        return GithubFile.model_validate(file_info)

    def get_workflow_list(self) -> list[Workflow]:
        """
        Fetches a list of workflows available to trigger

        Returns:
            list[Workflow]: List of workflows available to trigger
        """
        resp = self._get_object(path="/actions/workflows")
        return [Workflow.model_validate(workflow) for workflow in resp["workflows"]]

    def trigger_workflow_run(self, workflow_url: str, inputs: dict) -> dict:
        """
        Triggers a worflow run with the given workflow url.

        Args:
            workflow_url (str): URL of workflow to trigger
            inputs (dict): Inputs and ref to pass to workflow
        """
        self._post_request(
            url=f"{workflow_url}/dispatches",
            data={
                "ref": "main",
                "inputs": inputs,
            },
        )

    def fetch_in_progress_workflow_runs(self) -> list[WorkflowRun]:
        """
        Fetches a list of workflow runs which an in progress

        Returns:
            list[WorkflowRun]: Listof workflow runs
        """
        workflow_runs = []
        for status in [WorkFlowStatus.QUEUED, WorkFlowStatus.IN_PROGRESS]:
            resp = self._get_object(
                path="/actions/runs",
                custom_params={
                    "params": {
                        "status": status,
                    }
                },
            )

            workflow_runs.extend(
                [
                    WorkflowRun.model_validate(workflow_run)
                    for workflow_run in resp["workflow_runs"]
                ]
            )
        return workflow_runs

    def fetch_jobs(self, jobs_url: str) -> list[WorkflowJob]:
        """
        Fetches a list of workflow jobs

        Args:
            jobs_url (str): The URL for fetching workflow jobs

        Returns:
            list[WorkflowJob]: List of workflow jobs
        """
        resp = self._get_object(url=jobs_url)
        return [WorkflowJob.model_validate(job) for job in resp["jobs"]]
