"""Tests for the Supabase Storage resume PDF client."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.db import storage


def test_resume_storage_path_is_scoped_to_candidate_and_resume():
    path = storage.resume_storage_path("candidate-1", "resume-1")

    assert path == "candidate-1/resume-1.pdf"


def test_resume_storage_path_never_collides_across_resumes():
    first = storage.resume_storage_path("candidate-1", "resume-1")
    second = storage.resume_storage_path("candidate-1", "resume-2")

    assert first != second


def test_upload_raises_when_storage_is_not_configured(monkeypatch):
    monkeypatch.setattr(storage, "SUPABASE_URL", None)
    monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", None)

    with pytest.raises(storage.StorageUploadError, match="not configured"):
        storage.upload_resume_pdf("candidate-1/resume-1.pdf", b"%PDF-1.4\n...")


def test_upload_raises_on_non_2xx_response(monkeypatch):
    monkeypatch.setattr(storage, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setattr(
        httpx, "post", MagicMock(return_value=MagicMock(status_code=400))
    )

    with pytest.raises(storage.StorageUploadError, match="400"):
        storage.upload_resume_pdf("candidate-1/resume-1.pdf", b"%PDF-1.4\n...")


def test_upload_raises_on_network_error(monkeypatch):
    monkeypatch.setattr(storage, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setattr(
        httpx, "post", MagicMock(side_effect=httpx.ConnectTimeout("timed out"))
    )

    with pytest.raises(storage.StorageUploadError, match="Failed to reach Supabase Storage"):
        storage.upload_resume_pdf("candidate-1/resume-1.pdf", b"%PDF-1.4\n...")


def test_upload_succeeds_on_2xx_and_sends_expected_request(monkeypatch):
    monkeypatch.setattr(storage, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setattr(storage, "SUPABASE_RESUME_BUCKET", "resumes")
    post = MagicMock(return_value=MagicMock(status_code=200))
    monkeypatch.setattr(httpx, "post", post)

    storage.upload_resume_pdf("candidate-1/resume-1.pdf", b"%PDF-1.4\nbody")

    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "https://project.supabase.co/storage/v1/object/resumes/candidate-1/resume-1.pdf"
    assert kwargs["headers"]["Authorization"] == "Bearer service-role-key"
    assert kwargs["headers"]["apikey"] == "service-role-key"
    assert kwargs["headers"]["Content-Type"] == "application/pdf"
    assert kwargs["content"] == b"%PDF-1.4\nbody"
