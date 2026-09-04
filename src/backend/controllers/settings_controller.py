"""Controller Layer - Settings Controller.

Runtime-toggleable app settings exposed to the frontend, currently just
FIXED_TOOLS_ENABLED (config.settings) - lets the demo UI flip it without a
process restart, unlike editing `.env`. See
backend.services.chat_service._get_agent_executor() for how a toggle here
is picked up by the next chat turn.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class FixedToolsEnabledResponse(BaseModel):
    fixed_tools_enabled: bool


class FixedToolsEnabledRequest(BaseModel):
    fixed_tools_enabled: bool


@router.get("/fixed-tools-enabled", response_model=FixedToolsEnabledResponse)
def get_fixed_tools_enabled() -> FixedToolsEnabledResponse:
    """Current FIXED_TOOLS_ENABLED state, for the frontend to initialize its toggle."""
    return FixedToolsEnabledResponse(fixed_tools_enabled=settings.is_fixed_tools_enabled())


@router.put("/fixed-tools-enabled", response_model=FixedToolsEnabledResponse)
def set_fixed_tools_enabled(request: FixedToolsEnabledRequest) -> FixedToolsEnabledResponse:
    """Flip FIXED_TOOLS_ENABLED at runtime - takes effect on the next chat turn."""
    settings.set_fixed_tools_enabled(request.fixed_tools_enabled)
    return FixedToolsEnabledResponse(fixed_tools_enabled=settings.is_fixed_tools_enabled())
