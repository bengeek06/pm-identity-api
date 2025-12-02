"""
Module: app.email_helper

Email utility functions for sending password reset OTP emails.
"""

from flask import current_app
from flask_mail import Mail, Message

from app.logger import logger

mail = Mail()


def send_password_reset_email(
    email: str, otp_code: str, user_name: str = None
):
    """
    Send password reset OTP email to user.

    Args:
        email: Recipient email address
        otp_code: 6-digit OTP code (plain text, not hashed)
        user_name: Optional user name for personalization

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not current_app.config.get("USE_EMAIL_SERVICE"):
        logger.warning(
            "Email service is disabled. Cannot send password reset email."
        )
        return False

    try:
        greeting = f"Hello {user_name}" if user_name else "Hello"

        msg = Message(
            subject="Password Reset Request - Waterfall Identity Service",
            recipients=[email],
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        )

        # Plain text body
        msg.body = f"""{greeting},

You have requested to reset your password for Waterfall Identity Service.

Your password reset code is: {otp_code}

This code will expire in {current_app.config.get('PASSWORD_RESET_OTP_TTL_MINUTES', 15)} minutes.

If you did not request this password reset, please ignore this email.

Best regards,
Waterfall Identity Service Team
"""

        # HTML body
        msg.html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #4CAF50; text-align: center;
                     padding: 20px; background-color: #fff; border: 2px solid #4CAF50;
                     border-radius: 5px; margin: 20px 0; letter-spacing: 5px; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        .warning {{ color: #f44336; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>{greeting},</p>
            <p>You have requested to reset your password for Waterfall Identity Service.</p>
            <p>Your password reset code is:</p>
            <div class="otp-code">{otp_code}</div>
            <p>This code will expire in <strong>
            {current_app.config.get('PASSWORD_RESET_OTP_TTL_MINUTES', 15)}
            minutes</strong>.</p>
            <p class="warning">If you did not request this password reset,
            please ignore this email and contact support immediately.</p>
        </div>
        <div class="footer">
            <p>Waterfall Identity Service Team</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
"""

        mail.send(msg)
        logger.info("Password reset email sent to %s", email)
        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error(
            "Failed to send password reset email to %s: %s", email, str(e)
        )
        return False
