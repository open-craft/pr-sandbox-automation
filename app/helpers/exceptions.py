"""
Custom Exceptions
"""

from fastapi import HTTPException


class ObjectDoesNotExist(Exception):
    """
    Exception raised when accessing an object that does not exist.
    """


class RateLimitExceeded(Exception):
    """
    Exception raised when accessing an object and a rate limit is hit.
    """


class DBOperationException(HTTPException):
    """
    Exception raised during DB Operations.
    """

    def __init__(self, msg: str):
        detail = [{"type": "db_operation_exception", "loc": ["body"], "msg": msg}]
        super().__init__(status_code=500, detail=detail)


class UnactionableRequestException(HTTPException):
    """
    Exception raised when request in found defective.
    """

    def __init__(self, msg: str):
        detail = [{"type": "request_not_actionable", "loc": ["body"], "msg": msg}]
        super().__init__(status_code=422, detail=detail)


class ClusterWorkflowNotFoundException(HTTPException):
    """
    Exception raised when a sepcific active workflow is not found.
    """

    def __init__(self, msg: str):
        detail = [{"type": "cluster_workflow_not_found", "loc": ["body"], "msg": msg}]
        super().__init__(status_code=422, detail=detail)


class ActiveCheckrunNotFoundException(HTTPException):
    """
    Exception raised when an active checkrun is not found for a given sandbox.
    """

    def __init__(self, msg: str):
        detail = [{"type": "active_checkrun_not_found", "loc": ["body"], "msg": msg}]
        super().__init__(status_code=422, detail=detail)
