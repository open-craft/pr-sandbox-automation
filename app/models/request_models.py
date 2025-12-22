"""
Custom request and header models used by the APIs
"""

from base64 import b64decode
from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    AliasPath,
    AliasChoices,
    ConfigDict,
)
import hashlib
import re
import yaml

from app.helpers.constants import (
    GithubActionTypes,
    GithubEventTypes,
    PullRequestState,
    ArgoCDSyncStatus,
    NamedRelease,
    WorkFlowStatus,
    WorkFlowConclusion,
    MANDATORY_TUTOR_PLUGINS,
    MFE_REPO_NAME_PREFIX,
    PR_SANDBOX_NAME_PATTERN,
)


class GithubFile(BaseModel):
    """
    Utility class representing a Github file.

    See https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#get-repository-content
    """

    name: str
    path: str
    file_sha: str = Field(alias=AliasPath("sha"))
    size: int
    url: str
    html_url: str
    download_url: str
    type: str
    encoding: str
    content: bytes

    model_config = ConfigDict(coerce_numbers_to_str=True)

    @property
    def content_as_dict(self) -> dict:
        """
        Returns the fetched files content as a dictionary.
        """
        return yaml.safe_load(self.content_as_string)

    @property
    def content_as_string(self) -> str:
        """
        Returns the fetched files content as a string.
        """
        return b64decode(self.content).decode("utf8")


class Workflow(BaseModel):
    """
    Model representing the workflow definition
    """

    id: str
    type: str = Field(alias=AliasPath("name"))
    state: str
    url: str
    html_url: str

    model_config = ConfigDict(coerce_numbers_to_str=True)


class WorkflowRun(BaseModel):
    """
    Model representing a workflow run
    """

    id: str
    name: str
    status: WorkFlowStatus
    conclusion: WorkFlowConclusion | None = None
    workflow_id: str
    attempt: int = Field(alias=AliasPath("run_attempt"))
    url: str = Field(alias=AliasPath("workflow_url"))
    jobs_url: str
    cancel_url: str
    rerun_url: str
    repo_url: str = Field(alias=AliasPath("repository", "url"))

    model_config = ConfigDict(coerce_numbers_to_str=True)

    @property
    def sandbox_name(self) -> str:
        """
        Extracts the value of a setting from the PR body.
        """
        if match := re.search(PR_SANDBOX_NAME_PATTERN, self.name):
            return match.group().strip()


class WorkflowJob(BaseModel):
    """
    Model representing a workflow job
    """

    id: str
    name: str
    url: str
    status: WorkFlowStatus
    conclusion: WorkFlowConclusion | None = None
    workflow_run_id: str = Field(alias=AliasPath("run_id"))
    workflow_name: str
    workflow_run_url: str = Field(alias=AliasPath("run_url"))
    workflow_run_attempt: int = Field(alias=AliasPath("run_attempt"))

    model_config = ConfigDict(coerce_numbers_to_str=True)

    @property
    def sandbox_name(self) -> str:
        """
        Extracts the value of a setting from the PR body.
        """
        if match := re.search(PR_SANDBOX_NAME_PATTERN, self.workflow_name):
            return match.group().strip()

    @property
    def workflow_type(self) -> str:
        return self.name.split("/")[0].strip()

    @property
    def workflow_job_type(self) -> str:
        return self.name.split("/")[1].strip()

    @property
    def logs_url(self) -> str:
        return f"{self.url}/logs"


class PullRequest(BaseModel):
    """
    Model representing the pull_request information in PR webhook request
    """

    labels: list[dict] = []
    url: str
    html_url: str
    comments_url: str
    number: str
    title: str
    state: PullRequestState
    author: str = Field(alias=AliasPath("user", "login"))
    body: str | None = None
    fork_name: str = Field(alias=AliasPath("head", "repo", "full_name"))
    repo_name: str = Field(alias=AliasPath("base", "repo", "name"))
    repo_html_url: str = Field(alias=AliasPath("base", "repo", "html_url"))
    branch_name: str = Field(alias=AliasPath("head", "ref"))
    target_branch: str = Field(alias=AliasPath("base", "ref"))
    commit_sha: str = Field(alias=AliasPath("head", "sha"))
    clone_url: str = Field(alias=AliasPath("head", "repo", "clone_url"))

    model_config = ConfigDict(coerce_numbers_to_str=True)

    @property
    def flat_labels(self) -> list[str]:
        return [label["name"] for label in self.labels]

    @property
    def extra_settings(self) -> str:
        """
        Returns the extra settings from the PR body.
        """
        return self.__extract_from_body(r"[Ss]ettings", self.body) or ""

    @property
    def tutor_requirements(self) -> list[str]:
        """
        Returns the tutor requirements from the PR body.
        """
        tutor_requirements_text = self.__extract_from_body(
            r"[Tt]utor\ requirements", self.body
        )

        if tutor_requirements_text:
            tutor_requirements = tutor_requirements_text.splitlines()
            # Check if supplied tutor requirements is missing any mandatory plugin
            missing_plugins = list(
                filter(
                    lambda r: not self.__find_git_repo(tutor_requirements, r),
                    MANDATORY_TUTOR_PLUGINS.keys(),
                )
            )
            # Get the correct pip install commands for the missing plugins for the release
            install_missing_plugins = [
                self.__find_git_repo(self.named_release.tutor_requirements, plugin)
                for plugin in missing_plugins
            ]
            # Get the commands to enable the missing plugins
            enable_missing_plugins = [
                f"tutor plugins enable {MANDATORY_TUTOR_PLUGINS[plugin]}"
                for plugin in missing_plugins
            ]
            return install_missing_plugins + enable_missing_plugins + tutor_requirements
        return self.named_release.tutor_requirements

    @property
    def sandbox_name(self) -> str:
        """
        Returns the name of the sandbox environment that should be created for
        this pull request.
        """
        hash_object = hashlib.sha1(self.fork_name.encode("utf8"))
        fork_hash = hash_object.hexdigest()[:6]
        return f"pr-{self.number}-{fork_hash}"

    @property
    def named_release(self) -> NamedRelease:
        """
        Returns the name of the target release.
        """
        branch_release_name = self.target_branch.split("/")[-1]
        return NamedRelease(branch_release_name.split(".")[0])

    @property
    def mfe_name(self) -> str:
        """
        Returns a resonable MFE name based on the repository name.
        """
        return self.fork_name.split(MFE_REPO_NAME_PREFIX, 1)[-1]

    def __str__(self) -> str:
        """
        Returns a string representation of the pull request.
        """
        return f"Pull request {self.title} (#{self.number}) by {self.author}"

    def has_activity(self, days: int) -> bool:
        """
        Returns whether the pull request has activity since the given date.
        """
        since_last_update = datetime.now() - self.updated_at
        return since_last_update.days <= days

    def __extract_from_body(self, key: str, body: str | None) -> str | None:
        """
        Extracts the value of a setting from the PR body.
        """
        pattern = (
            f"..{key}..((\\r)?\\n)+(```(?P<format>[a-z]+)?)\r?\n(?P<content>[^`]*?)```"
        )
        if body:
            has_match = re.search(pattern, body, flags=re.DOTALL)
            return has_match.group("content").strip() if has_match else None
        return None

    def __find_git_repo(self, all_requirements: list[str], repo: str) -> str | None:
        """
        Checks if the requirements include the given repo and returns it if found.
        """
        return next(filter(lambda r: re.search(repo, r), all_requirements), None)


class GithubWebhookRequest(BaseModel):
    """
    Custom request model to validate data fields for Github requests
    """

    github_action: GithubActionTypes = Field(
        alias="action",
        description="Indicates which action in Github initiated this webhook request.",
    )
    installation_id: str = Field(alias=AliasPath("installation", "id"))
    head_sha: str = Field(
        alias=AliasChoices(
            AliasPath("pull_request", "head", "sha"),
            AliasPath("check_run", "head_sha"),
            AliasPath("check_suite", "head_sha"),
            AliasPath("workflow_run", "head_sha"),
        )
    )
    app_id: str | None = Field(
        alias=AliasChoices(
            AliasPath("check_suite", "app", "id"), AliasPath("check_run", "app", "id")
        ),
        default=None,
    )
    repo_name: str = Field(alias=AliasPath("repository", "full_name"))
    repository_url: str = Field(alias=AliasPath("repository", "url"))
    action_label: str = Field(alias=AliasPath("label", "name"), default="")
    check_run_id: str | None = Field(alias=AliasPath("check_run", "id"), default=None)
    check_suite_id: str | None = Field(
        alias=AliasChoices(
            AliasPath("check_suite", "id"), AliasPath("check_run", "check_suite", "id")
        ),
        default=None,
    )
    pull_request: PullRequest | None = None
    workflow_run: WorkflowRun | None = None
    workflow: Workflow | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True)


class GithubWebhookHeader(BaseModel):
    """
    Custom header model to filter out unsupported Github events
    """

    x_github_event: GithubEventTypes
    x_hub_signature_256: str


class ArgoWebhookRequest(BaseModel):
    """
    Custom request model to validate data fields for ArgoCD requests
    """

    application: str
    state: ArgoCDSyncStatus

    @property
    def sandbox_name(self) -> str:
        """
        Extracts the sandbox name from argocd application name.
        """
        if match := re.search(PR_SANDBOX_NAME_PATTERN, self.application):
            return match.group().strip()
