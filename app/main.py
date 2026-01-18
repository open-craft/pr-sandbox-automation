"""
Entry point for FastAPI
"""

import logging
from fastapi import FastAPI

from app.handlers import github_webhook_router, argocd_webhook_router, web_router
from app.helpers.conf import config

if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )

# Initialize the FastAPI application
app = FastAPI(
    title="PR Sandbox Automation", description="Automatically manage sandboxes for PRs"
)
app.include_router(github_webhook_router)
app.include_router(argocd_webhook_router)
app.include_router(web_router)
