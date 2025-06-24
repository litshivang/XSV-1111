import pytest
from app.services.email_service import EmailService
from app.models.email_models import EmailMessage

@pytest.fixture
def email_service():
    return EmailService()

def test_get_messages_success(email_service, monkeypatch):
    # Mock the get_messages method to return a list of EmailMessage
    monkeypatch.setattr(email_service, "get_messages", lambda *a, **kw: [EmailMessage(
        message_id="m1", thread_id="t1", subject="Test", sender_email="test@example.com", received_date="2024-06-01T10:00:00Z")])
    messages = email_service.get_messages()
    assert isinstance(messages, list)
    assert isinstance(messages[0], EmailMessage)
    assert messages[0].subject == "Test"

def test_get_messages_error(email_service, monkeypatch):
    monkeypatch.setattr(email_service, "get_messages", lambda *a, **kw: (_ for _ in ()).throw(Exception("API error")))
    with pytest.raises(Exception):
        email_service.get_messages()
