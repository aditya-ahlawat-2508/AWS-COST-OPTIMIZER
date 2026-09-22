import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import CopilotChatRequest, CopilotChatResponse

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(
    payload: CopilotChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CopilotChatResponse:
    # Imported lazily so importing this router (and therefore booting the API)
    # never requires ANTHROPIC_API_KEY to be set or the anthropic package's
    # client construction to succeed.
    import anthropic

    from services.copilot.agent import chat

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Copilot is not configured: ANTHROPIC_API_KEY is not set",
        )

    try:
        client = anthropic.Anthropic()
        result = chat(client, db, user.org_id, user.id, payload.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Copilot request failed: {exc}"
        )
    return CopilotChatResponse(
        text=result.text,
        tool_calls=[tc["name"] for tc in result.tool_calls],
        grounding_warnings=result.grounding_warnings,
    )
