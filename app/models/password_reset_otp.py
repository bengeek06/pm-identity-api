"""
Module: app.models.password_reset_otp

Defines the PasswordResetOTP model for temporary OTP storage.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

# Import db from app.models - cyclic import is intentional and safe here
# pylint: disable=cyclic-import
from app.models import db


class PasswordResetOTP(db.Model):
    """
    Model for password reset OTP tokens.

    Stores temporary OTP codes with expiration and attempt tracking.
    """

    __tablename__ = "password_reset_otp"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    otp_code: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Hashed OTP for security
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    @staticmethod
    def create_otp(user_id: str, otp_code_hash: str, ttl_minutes: int = 15):
        """
        Create a new OTP for password reset.

        Args:
            user_id: User ID for whom the OTP is created
            otp_code_hash: Hashed OTP code
            ttl_minutes: Time to live in minutes (default: 15)

        Returns:
            PasswordResetOTP: Created OTP instance
        """
        otp = PasswordResetOTP(
            user_id=user_id,
            otp_code=otp_code_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=ttl_minutes),
        )
        db.session.add(otp)
        return otp

    @staticmethod
    def get_valid_otp(user_id: str):
        """
        Get the most recent valid (not expired, not used) OTP for a user.

        Args:
            user_id: User ID

        Returns:
            PasswordResetOTP or None: Valid OTP if found
        """
        now = datetime.now(timezone.utc)
        return (
            PasswordResetOTP.query.filter_by(user_id=user_id, used_at=None)
            .filter(PasswordResetOTP.expires_at > now)
            .order_by(PasswordResetOTP.created_at.desc())
            .first()
        )

    @staticmethod
    def invalidate_all_for_user(user_id: str):
        """
        Invalidate all OTPs for a user by marking them as used.

        Args:
            user_id: User ID
        """
        now = datetime.now(timezone.utc)
        PasswordResetOTP.query.filter_by(user_id=user_id, used_at=None).update(
            {"used_at": now}
        )

    def is_valid(self) -> bool:
        """Check if OTP is still valid (not expired, not used, attempts < 3)."""
        now = datetime.now(timezone.utc)
        # Handle SQLite naive datetimes
        expires_at = (
            self.expires_at.replace(tzinfo=timezone.utc)
            if self.expires_at.tzinfo is None
            else self.expires_at
        )
        return self.used_at is None and expires_at > now and self.attempts < 3

    def mark_used(self):
        """Mark OTP as used."""
        self.used_at = datetime.now(timezone.utc)

    def increment_attempts(self):
        """Increment failed verification attempts."""
        self.attempts += 1
