import logging
import math
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserCredit, VideoAnalysis

logger = logging.getLogger(__name__)


def _current_yyyymm() -> int:
    now = datetime.now(timezone.utc)
    return now.year * 100 + now.month


def compute_credit_cost(file_size_bytes: int) -> int:
    return max(1, math.ceil(file_size_bytes / (1024 * 1024)))


def get_user_credit(db: Session, user_id: int) -> UserCredit:
    credit = db.query(UserCredit).filter(UserCredit.user_id == user_id).first()
    current_month = _current_yyyymm()

    if credit is None:
        credit = UserCredit(
            user_id=user_id,
            balance=settings.monthly_credits,
            last_reset_month=current_month,
        )
        db.add(credit)
        db.flush()
        logger.info("Credits initialized — user_id=%d balance=%d", user_id, settings.monthly_credits)
        return credit

    if credit.last_reset_month < current_month:
        old_balance = credit.balance
        credit.balance = settings.monthly_credits
        credit.last_reset_month = current_month
        db.flush()
        logger.info("Monthly credit reset — user_id=%d old=%d new=%d", user_id, old_balance, settings.monthly_credits)

    return credit


def get_daily_upload_count(db: Session, user_id: int) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    return (
        db.query(VideoAnalysis)
        .filter(
            VideoAnalysis.user_id == user_id,
            VideoAnalysis.created_at >= today_start,
            VideoAnalysis.status == "completed",
        )
        .count()
    )


def check_upload_allowed(db: Session, user_id: int, file_size_bytes: int) -> str | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role == "admin":
        return None

    daily_count = get_daily_upload_count(db, user_id)
    if daily_count >= settings.daily_video_limit:
        return (
            f"Daily upload limit reached ({settings.daily_video_limit} videos per day). "
            f"Please try again tomorrow."
        )

    credit = get_user_credit(db, user_id)
    cost = compute_credit_cost(file_size_bytes)
    if cost > credit.balance:
        return (
            f"Insufficient credits. This video requires {cost} credit(s) "
            f"but you only have {credit.balance} remaining. "
            f"Credits reset at the start of each month."
        )

    return None


def deduct_credits(db: Session, user_id: int, file_size_bytes: int) -> int:
    credit = get_user_credit(db, user_id)
    cost = compute_credit_cost(file_size_bytes)
    credit.balance -= cost
    db.flush()
    logger.info("Credits deducted — user_id=%d cost=%d remaining=%d", user_id, cost, credit.balance)
    return cost


def refund_credits(db: Session, user_id: int, amount: int) -> None:
    credit = get_user_credit(db, user_id)
    credit.balance = min(credit.balance + amount, settings.monthly_credits)
    db.flush()
    logger.info("Credits refunded — user_id=%d amount=%d new_balance=%d", user_id, amount, credit.balance)


def admin_set_credits(db: Session, user_id: int, new_balance: int) -> UserCredit:
    credit = get_user_credit(db, user_id)
    old_balance = credit.balance
    credit.balance = new_balance
    db.flush()
    logger.info("Admin credit override — user_id=%d old=%d new=%d", user_id, old_balance, new_balance)
    return credit
