import pytest


@pytest.fixture(autouse=True)
def configured_resume_storage(monkeypatch):
    """Run the API tests as a deployment that has Supabase Storage configured.

    Resume upload refuses outright when Storage credentials are absent, which is
    correct but is not what these tests are about; the test covering that
    refusal opts back out by patching the same function itself. Storage calls
    are still mocked per test -- this only decides what the server believes it
    is configured to do.
    """
    from app.db import storage

    monkeypatch.setattr(storage, "is_configured", lambda: True)
