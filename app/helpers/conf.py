"""
Configuration of the function parsed from the environment variables.

The environment variables that are prefixed with `PR_SANDBOX_` are parsed as
settings for the root configuration object. All configuration objects have their
corresponding environment variables prefixed with their name in uppercase.

For example, the configuration object `openedx` has its environment variables
prefixed with `OPENEDX_`. The configuration object `openedx_instance` has its
environment variables prefixed with `OPENEDX_INSTANCE_`.

The module have a `config` object that contains the parsed configuration. When
the module is imported, the configuration is parsed from the environment
variables and stored in the `config` object. Hence, before importing this
module, the environment variables must be set.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Config(BaseSettings):
    """
    PR sandox app config.
    """

    user_agent: str = "pr-sandbox-automation/v1.0.0"
    github_app_identifier: str = Field(
        description="Identifier for the Github App",
    )

    pr_label: str = Field(
        "create-sandbox",
        description="PR label to mark PR for automated sandbox management.",
    )

    cluster_github_repo_url: str = Field(
        description="Repository URL for the PHD cluster repo",
    )

    default_platform_url: str = Field(
        "https://github.com/openedx/edx-platform.git",
        description="Default URL of the edx-platform repository.",
    )

    default_platform_branch: str = Field(
        "master",
        description="Default branch of the edx-platform repository.",
    )

    argocd_app_url: str = Field(
        description="URL to view pods/jobs status in argocd for an application"
    )

    app_logs_url: str = Field(
        description="The URL for this application for PR authors to view workflow job logs"
    )
    
    max_run_attempt: int = Field(
        2,
        description="The maximum number of times a workflow run will be attempted.",
    )

    max_sandbox_count: int = Field(
        30,
        description="The maximum number of active sandboxes allowed.",
    )

    log_level: str = Field(
        "INFO",
        description="Level of the logs.",
    )

    db_debug_logging: bool = Field(
        False,
        description="Flag to log debug information for every DB operation.",
    )

    model_config = SettingsConfigDict(env_prefix="PR_SANDBOX_")


config = Config()
