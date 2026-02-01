"""
A list of constants used through the application
"""

from enum import StrEnum

MANDATORY_TUTOR_PLUGINS = {
    "tutor-contrib-drydock": "drydock",
    # "tutor-contrib-harmony-plugin": "k8s_harmony",
    # "tutor-contrib-mfe-extensions": "mfe-extensions",
}

NAMED_RELEASE_SUMAC = "sumac"
NAMED_RELEASE_TEAK = "teak"
NAMED_RELEASE_ULMO = "ulmo"
NAMED_RELEASE_MASTER = "master"  # Special case for master branch

NAMED_RELEASE_LATEST_COMMON_VERSIONS: dict[str, str] = {
    NAMED_RELEASE_SUMAC: "open-release/sumac.master",
    NAMED_RELEASE_TEAK: "release/teak",
    NAMED_RELEASE_ULMO: "release/ulmo",
    NAMED_RELEASE_MASTER: "master",
}

NAMED_RELEASE_TUTOR_REQUIREMENTS: dict[str, list[str]] = {
    NAMED_RELEASE_SUMAC: [
        "tutor>=19,<20",
        "tutor-discovery>=19,<20",
        "tutor-ecommerce>=19,<20",
        "tutor-mfe>=19,<20",
        "tutor-xqueue>=19,<20",
        "git+https://github.com/overhangio/tutor-forum.git@release",  # change to tag when new tag after v19.0.0 is released.
        "git+https://gitlab.com/opencraft/dev/tutor-contrib-grove.git@main",
        "git+https://github.com/hastexo/tutor-contrib-s3.git@v2.1.0",
        "git+https://github.com/openedx/openedx-k8s-harmony.git@main#egg=tutor-contrib-harmony&subdirectory=tutor-contrib-harmony-plugin",
    ],
    NAMED_RELEASE_TEAK: [
        "pip install tutor-contrib-drydock",
        "pip install tutor-mfe>=20,<21",
        "pip install tutor-forum>=20,<21",
        # "pip install git+https://gitlab.com/opencraft/dev/tutor-contrib-grove.git@main",
        "pip install git+https://github.com/hastexo/tutor-contrib-s3.git@v2.3.1",
        # "pip install git+https://github.com/openedx/openedx-k8s-harmony.git@main#egg=tutor-contrib-harmony&subdirectory=tutor-contrib-harmony-plugin",
        "tutor plugins enable drydock mfe forum s3",
        "tutor config save",
    ],
    NAMED_RELEASE_ULMO: [
        "pip install tutor-contrib-drydock",
        # "git+https://github.com/overhangio/tutor.git@ulmo",
        "pip install git+https://gitlab.com/opencraft/dev/tutor-contrib-grove@main",
        "pip install git+https://github.com/overhangio/tutor-mfe.git@ulmo",
        "pip install git+https://github.com/overhangio/tutor-forum.git@ulmo",
        # "pip install git+https://gitlab.com/opencraft/dev/tutor-contrib-grove.git@021249b92a1027792424206365786b22a3820cbb",  # change this when this issue is fixed https://forum.opencraft.com/t/the-future-of-simple-theme/1985/9?u=kaustav
        # "pip install git+https://github.com/open-craft/tutor-contrib-s3.git@kaustav/add_support_for_tutor_21",
        # "pip install git+https://github.com/open-craft/openedx-k8s-harmony.git@kaustav/support_tutor_21#egg=tutor-contrib-harmony&subdirectory=tutor-contrib-harmony-plugin",
        "tutor plugins enable drydock mfe forum grove-mfes",
        # "tutor plugins enable grove",
        # "tutor plugins enable k8s_harmony",
        "tutor config save",
    ],
    NAMED_RELEASE_MASTER: [
        "pip install tutor-contrib-drydock",
        # "git+https://github.com/overhangio/tutor.git@main",
        "pip install git+https://gitlab.com/opencraft/dev/tutor-contrib-grove@main",
        "pip install git+https://github.com/overhangio/tutor-mfe.git@main",
        "pip install git+https://github.com/overhangio/tutor-forum.git@main",
        # "pip install git+https://gitlab.com/opencraft/dev/tutor-contrib-grove.git@main",
        # "pip install git+https://github.com/hastexo/tutor-contrib-s3.git@main",
        # "pip install git+https://github.com/openedx/openedx-k8s-harmony.git@main#egg=tutor-contrib-harmony&subdirectory=tutor-contrib-harmony-plugin",
        "tutor plugins enable drydock mfe forum grove-mfes",
        # "tutor plugins enable grove-simple-theme",
        # "tutor plugins enable grove",
        # "tutor plugins enable k8s_harmony",
        "tutor config save",
    ],
}


NAMED_RELEASE_TUTOR_VERSIONS: dict[str, str] = {
    NAMED_RELEASE_SUMAC: "v19.0.5",
    NAMED_RELEASE_TEAK: "v20.0.2",
    NAMED_RELEASE_ULMO: "ulmo",
    NAMED_RELEASE_MASTER: "main",
}


class NamedRelease(StrEnum):
    """
    Possible named releases of Open edX that is supported by the pull request
    watcher.
    """

    SUMAC = NAMED_RELEASE_SUMAC
    TEAK = NAMED_RELEASE_TEAK
    ULMO = NAMED_RELEASE_ULMO
    MASTER = NAMED_RELEASE_MASTER
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value

    def values() -> list[str]:
        """
        Returns all the possible values of the enum.
        """
        return [str(release) for release in NamedRelease]

    @classmethod
    def _missing_(cls, value):
        return cls.MASTER

    @property
    def release_name(self) -> str:
        """
        Returns the release name of the named release.

        If the named release is unknown, the release name of the master branch
        is returned.
        """
        return self.value

    @property
    def tutor_requirements(self) -> list[str]:
        """
        Returns the necessary tutor requirements with their versions for the
        given named release.

        If the named release is unknown, the tutor requirements for the master
        branch are returned.
        """
        return NAMED_RELEASE_TUTOR_REQUIREMENTS.get(
            self.value, NAMED_RELEASE_TUTOR_REQUIREMENTS[NAMED_RELEASE_MASTER]
        )

    @property
    def tutor_version(self) -> str:
        """
        Returns the latest tutor version corresponding to the
        given named release.

        If the named release is unknown, the tutor requirements for the master
        branch are returned.
        """
        return NAMED_RELEASE_TUTOR_VERSIONS.get(
            self.value, NAMED_RELEASE_TUTOR_VERSIONS[NAMED_RELEASE_MASTER]
        )

    @property
    def latest_common_version(self) -> str:
        """
        Returns the latest common version of the named release.

        If the named release is unknown, the latest common version of the master
        branch is returned.
        """
        return NAMED_RELEASE_LATEST_COMMON_VERSIONS.get(
            self.value, NAMED_RELEASE_LATEST_COMMON_VERSIONS[NAMED_RELEASE_MASTER]
        )


class GithubActionTypes(StrEnum):
    """
    Valid Github action types.
    """

    REREQUESTED = "rerequested"
    SYNCHRONIZE = "synchronize"
    CLOSED = "closed"
    REOPENED = "reopened"
    LABELED = "labeled"
    UNLABELED = "unlabeled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class GithubEventTypes(StrEnum):
    """
    Valid Github event types
    """

    PULL_REQUEST = "pull_request"
    CHECK_RUN = "check_run"
    CHECK_SUITE = "check_suite"
    WORKFLOW_RUN = "workflow_run"


# Map of actions and events accepted by this application
GITHUB_EVENT_ACTION_MAP = {
    GithubEventTypes.PULL_REQUEST: [
        GithubActionTypes.SYNCHRONIZE,
        GithubActionTypes.CLOSED,
        GithubActionTypes.REOPENED,
        GithubActionTypes.LABELED,
        GithubActionTypes.UNLABELED,
    ],
    GithubEventTypes.CHECK_RUN: [
        GithubActionTypes.REREQUESTED,
    ],
    GithubEventTypes.CHECK_SUITE: [GithubActionTypes.REREQUESTED],
    GithubEventTypes.WORKFLOW_RUN: [
        GithubActionTypes.IN_PROGRESS,
        GithubActionTypes.COMPLETED,
    ],
}


class PullRequestState(StrEnum):
    """
    Possible states of a pull request.

    A pull request can have multiple states when it is opened or closed, but we
    are not making a distinction between them. We only care if it's open or not.
    """

    OPEN = "open"
    CLOSED = "closed"


class CheckRunStatus(StrEnum):
    """
    Valid Statuses for Check Runs
    """

    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"
    COMPLETE = "completed"
    FAILURE = "failure"
    SUCCESS = "success"


class SandboxStatus(StrEnum):
    """
    List of Statuses for Sandbox
    """

    CREATED = "created"
    UPDATED = "updated"
    DESTROYED = "destroyed"


class WorkflowType(StrEnum):
    """
    List of valid workflow names.
    """

    CREATE_INSTANCE = "Create Instance"
    UPDATE_INSTANCE = "Update Instance"
    BUILD_ALL_IMAGES = "Build All Images"
    DELETE_INSTANCE = "Delete Instance"


WORKFLOW_EXECUTION_ORDER = (
    WorkflowType.CREATE_INSTANCE,
    WorkflowType.UPDATE_INSTANCE,
    WorkflowType.BUILD_ALL_IMAGES,
)

WORKFLOW_HEADERS = {
    WorkflowType.CREATE_INSTANCE: "Generating Initial Sandbox Configs",
    WorkflowType.UPDATE_INSTANCE: "Customizing Sandbox Configs",
    WorkflowType.BUILD_ALL_IMAGES: "Building Service Images",
}


class WorkFlowStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETE = "completed"


class WorkFlowConclusion(StrEnum):
    SUCCESS = "success"
    NEUTRAL = "neutral"
    SKIPPED = "skipped"
    FAILURE = "failure"
    ACTION_REQUIRED = "action_required"
    CANCELLED = "cancelled"
    STALE = "stale"
    TIMED_OUT = "timed_out"


WORKFLOW_SUCCESS_CONCLUSION = [
    WorkFlowConclusion.SUCCESS,
    WorkFlowConclusion.NEUTRAL,
    WorkFlowConclusion.SKIPPED,
]


class ArgoCDSyncStatus(StrEnum):
    """
    Valid ArgoCD sync states
    """

    RUNNING = "Running"
    ERROR = "Error"
    FAILED = "Failed"
    SUCCEEDED = "Succeeded"


WORKFLOW_ACTIVE = "active"

MFE_REPO_NAME_PREFIX = "frontend-app-"
MFE_CUSTOM_PORT = 18000

SIGNATURE_PREFIX = "sha256="
SIGNATURE_HEADER = "x-hub-signature-256"

AUTHORIZATION_HEADER = "authorization"
AUTHORIZATION_PREFIX = "Basic "

CHECK_RUN_NAME = "sandbox_deployment"

PR_SANDBOX_NAME_PATTERN = r"pr-\d*-[0-9a-f]{6}"
