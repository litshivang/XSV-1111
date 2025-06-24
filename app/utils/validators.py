import re
from datetime import datetime
from .exceptions import ValidationError

def validate_email(email: str):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email address: {email}")


def validate_required_fields(data: dict, required_fields: list):
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


def validate_date(date_str: str, fmt: str = "%Y-%m-%d"):
    try:
        datetime.strptime(date_str, fmt)
    except Exception:
        raise ValidationError(f"Invalid date format: {date_str}. Expected format: {fmt}")
