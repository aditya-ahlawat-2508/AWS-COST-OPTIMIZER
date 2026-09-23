from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import NotificationSettings, Organization, User
from ..schemas import NotificationSettingsOut, NotificationSettingsUpdate, SendDigestResult

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/slack", response_model=NotificationSettingsOut)
def get_slack_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> NotificationSettingsOut:
    settings = db.get(NotificationSettings, user.org_id)
    return NotificationSettingsOut(slack_webhook_url=settings.slack_webhook_url if settings else None)


@router.put("/slack", response_model=NotificationSettingsOut)
def set_slack_settings(
    payload: NotificationSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> NotificationSettingsOut:
    settings = db.get(NotificationSettings, user.org_id)
    if settings is None:
        settings = NotificationSettings(org_id=user.org_id)
        db.add(settings)
    settings.slack_webhook_url = payload.slack_webhook_url
    db.flush()
    return NotificationSettingsOut(slack_webhook_url=settings.slack_webhook_url)


@router.post("/slack/send-digest", response_model=SendDigestResult)
def send_digest_now(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SendDigestResult:
    from services.notifications.digest import send_weekly_digest_for_org

    settings = db.get(NotificationSettings, user.org_id)
    if settings is None or not settings.slack_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No Slack webhook configured for this organization"
        )

    org = db.get(Organization, user.org_id)
    success = send_weekly_digest_for_org(db, user.org_id, org.name, settings.slack_webhook_url)
    return SendDigestResult(sent=success)
