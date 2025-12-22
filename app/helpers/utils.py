"""
Utility functions applicable to the whole project
"""

import os
from pathlib import Path

# Make the path configurable for testing
SECRET_DIR = os.getenv(
    "KUBERNETES_SECRET_DIR", "/var/run/secrets/kubernetes.io/serviceaccount"
)


def get_secret(name: str, raise_error: bool = True) -> str:
    """
    Return a secret mapped as a file by OpenFAAS.

    Args:
        name: name of the secret

    Returns:
        Value secret value from the file.
    """

    if not is_secret_exists(name):
        if not raise_error:
            return ""
        raise ValueError(f"Secret {name} not found")

    return open(get_secret_path(name), "r").read().strip()


def get_secret_path(name: str) -> Path:
    """
    Return the given secrets' absolute path.

    Args:
        name: name of the secret

    Returns:
        Absolute path for the named secret.
    """

    return Path(f"{SECRET_DIR}/{name}").absolute()


def is_secret_exists(name: str) -> bool:
    """
    Return whether the given secret exists.

    Args:
        name: name of the secret

    Returns:
        True if the secret exists, False otherwise.
    """

    return get_secret_path(name).exists()


def merge_dicts(dict1, dict2, append_lists=False):
    """Given two dict, merge the second dict into the first.

    The dicts can have arbitrary nesting.

    :param append_lists: If true, instead of clobbering a list with the new
        value, append all of the new values onto the original list.
    """
    for key in dict2:
        if isinstance(dict2[key], dict):
            if key in dict1 and key in dict2:
                merge_dicts(dict1[key], dict2[key])
            else:
                dict1[key] = dict2[key]
        # If the value is a list and the ``append_lists`` flag is set,
        # append the new values onto the original list
        elif isinstance(dict2[key], list) and append_lists:
            # The value in dict1 must be a list in order to append new
            # values onto it.
            if key in dict1 and isinstance(dict1[key], list):
                dict1[key].extend(dict2[key])
            else:
                dict1[key] = dict2[key]
        else:
            # At scalar types, we iterate and merge the
            # current dict that we're on.
            dict1[key] = dict2[key]
