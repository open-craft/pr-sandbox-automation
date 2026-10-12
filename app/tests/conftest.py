import json
import os
from pathlib import Path

from pytest import fixture
import fakeredis
from unittest.mock import patch

TEST_ASSETS_DIR = Path(__file__).parent / "assets"

MOCK_ENV_VARIABLES = {
    "OPENEDX_WATCHED_FORKS": '["open-craft/edx-platform"]',
    "OPENEDX_MFE_FORKS": '["open-craft/frontend-app-authn"]',
    "OPENEDX_DEFAULT_PLATFORM_URL": "https://github.com/open-craft/edx-platform",
    "GROVE_PROJECT_ID": "test",
    "GITHUB_AUTHORIZED_USERS": '["testuser"]',
    "GITHUB_AUTHORIZED_TEAMS": '["open-craft/testteam"]',
    "GITHUB_WATCHED_ORGANIZATIONS": '["open-craft"]',
    "DIGITALOCEAN_SPACES_ENDPOINT_REGION": "nyc3",
}


def pytest_configure(config):
    """
    Configure pytest before running any tests.
    """
    for k, v in MOCK_ENV_VARIABLES.items():
        os.environ.setdefault(k, v)


@fixture
def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@fixture
def mock_get_secret():
    # def return_secret_value(key):
    #     if key == "pr-sandbox-github-webhook-secret":
    #         return ""Large Number""
    #     return "Small Number"

    # # 2. Patch the function path and pass your custom function to side_effect
    # mocked_func = mocker.patch("math_utils.process_number", side_effect=dynamic_return)
    # return mocked_func
    with patch("app.helpers.utils.get_secret") as mock:
        mock.return_value = "abcd1234"
        yield mock


@fixture
def pull_request_labeled() -> dict:
    """
    Returns the github webhook request for pull request labeled event.
    """
    with open(TEST_ASSETS_DIR / "pull_request_labeled.json") as f:
        return json.loads(f.read())
