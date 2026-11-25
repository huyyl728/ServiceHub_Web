
import os
import secrets
import hashlib
import hmac
import smtplib
import ssl

from email.message import EmailMessage

# Thời gian hiệu lực của OTP: 5 phút
OTP_EXPIRY = 300

# Số lần nhập sai tối đa
MAX_ATTEMPTS = 5

# Thời gian chờ gửi lại OTP
RESEND_COOLDOWN = 60


def generate_otp():
    """Tạo mã OTP ngẫu nhiên gồm 6 chữ số."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(code, user_id):
    """Băm OTP bằng khóa bí mật của hệ thống."""
    key = os.environ.get("SERVICEHUB_OTP_SECRET", "")

    if len(key) < 32:
        raise RuntimeError("Chưa cấu hình khóa bảo mật OTP.")

    return hmac.new(
        key.encode(),
        f"{user_id}:{code}".encode(),
        hashlib.sha256
    ).hexdigest()


def verify_otp(code, stored_hash, user_id):
    """So sánh OTP với mã đã băm."""
    return hmac.compare_digest(
        hash_otp(code, user_id),
        stored_hash
    )


def send_otp_email(receiver, code):
    """Gửi mã OTP đến email người dùng."""

    sender = os.environ["SERVICEHUB_SMTP_EMAIL"]
    password = os.environ["SERVICEHUB_SMTP_PASSWORD"]

    message = EmailMessage()
    message["Subject"] = "Xác thực tài khoản ServiceHub"
    message["From"] = sender
    message["To"] = receiver

    message.set_content(
        f"Mã xác thực tài khoản ServiceHub của bạn là: {code}\n\n"
        "Mã có hiệu lực trong 5 phút.\n"
        "Không chia sẻ mã này với người khác."
    )

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=ssl.create_default_context(),
        timeout=15
    ) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)
