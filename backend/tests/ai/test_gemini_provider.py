"""Tests for Gemini provider implementation."""

import pytest
from unittest.mock import MagicMock, patch

from google.genai import errors as genai_errors

from app.ai.llm.gemini_provider import (
    MAX_RETRY_DELAY_SECONDS,
    RETRY_BACKOFF_SECONDS,
    GeminiProvider,
    LLMUnavailableError,
    call_with_retry,
    server_retry_delay,
)
from app.schemas.resume import CandidateProfile

MODEL = "gemini-3.6-flash"

VALID_PROFILE_JSON = (
    '{"identity":{"full_name":null,"email":null,"phone":null,"location":null,'
    '"resume_evidence":null},"professional_summary":null,"education":[],"skills":[],'
    '"technologies":[],"experience":[],"projects":[],"certifications":[],'
    '"achievements":[],"claims":[],"languages":[]}'
)


def api_error(status_code: int) -> genai_errors.APIError:
    return genai_errors.APIError(status_code, {"error": {"message": "upstream"}})


def test_gemini_provider_initialization_success():
    """Test successful Gemini provider initialization."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        provider = GeminiProvider(api_key="test-key", model=MODEL)

        assert provider.model == MODEL
        assert mock_client.call_args.kwargs["api_key"] == "test-key"


def test_gemini_provider_reuses_one_client_per_api_key():
    """A second provider on the same key must not build a second client."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        first = GeminiProvider(api_key="shared-key", model=MODEL)
        second = GeminiProvider(api_key="shared-key", model=MODEL)

        assert first.client is second.client
        mock_client.assert_called_once()


def test_gemini_provider_initialization_missing_api_key():
    """Test Gemini provider initialization fails without API key."""
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiProvider(api_key=None, model=MODEL)


def test_gemini_provider_initialization_missing_model():
    """Test Gemini provider initialization fails without model."""
    with pytest.raises(ValueError, match="GEMINI_MODEL is required"):
        GeminiProvider(api_key="test-key", model=None)


def test_gemini_provider_generate_success():
    """Test successful text generation with Gemini provider."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)
        result = provider.generate("Test prompt")

        assert result == "Generated response"
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == MODEL
        assert call_args.kwargs["contents"] == "Test prompt"


def test_gemini_provider_disables_automatic_function_calling():
    """No tools are ever passed, so the SDK's call loop is explicitly disabled."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = MagicMock(text="ok")

        GeminiProvider(api_key="test-key", model=MODEL).generate("Test prompt")

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.automatic_function_calling.disable is True


def test_gemini_provider_generate_handles_errors():
    """Test Gemini provider handles generation errors."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError, match="Gemini generation failed"):
            provider.generate("Test prompt")


def test_gemini_provider_generate_structured_success():
    """Test successful structured generation with Gemini provider."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = VALID_PROFILE_JSON
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)
        result = provider.generate_structured("Test prompt", CandidateProfile)

        assert isinstance(result, CandidateProfile)
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == MODEL
        assert call_args.kwargs["contents"] == "Test prompt"
        assert call_args.kwargs["config"].response_schema is CandidateProfile


def test_gemini_provider_generate_structured_handles_api_error():
    """Test Gemini provider handles structured generation API errors."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError, match="Gemini structured generation failed"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_generate_structured_handles_validation_error():
    """Test Gemini provider handles validation errors in structured generation."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"invalid": "data"}'
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(ValueError, match="Failed to parse response as"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_reports_an_empty_response_as_unavailable():
    """A truncated or filtered response has no text; that is not a parse failure."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = None
        mock_response.candidates = [MagicMock(finish_reason="MAX_TOKENS")]
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError, match="MAX_TOKENS"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_retries_a_transient_upstream_failure():
    """A 503 means the request was never processed, so re-sending it is safe."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.time.sleep"
    ) as mock_sleep:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        succeeded = MagicMock()
        succeeded.text = VALID_PROFILE_JSON
        mock_client.models.generate_content.side_effect = [api_error(503), succeeded]

        provider = GeminiProvider(api_key="test-key", model=MODEL)
        result = provider.generate_structured("Test prompt", CandidateProfile)

        assert isinstance(result, CandidateProfile)
        assert mock_client.models.generate_content.call_count == 2
        mock_sleep.assert_called_once()


def test_gemini_provider_does_not_retry_a_client_error():
    """A 400 fails identically every time; retrying only wastes the caller's time."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = api_error(400)

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError):
            provider.generate_structured("Test prompt", CandidateProfile)
        assert mock_client.models.generate_content.call_count == 1


def test_gemini_provider_gives_up_after_the_retry_budget():
    """Retrying is bounded: a persistent outage must surface, not loop forever."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.time.sleep"
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = api_error(503)

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError):
            provider.generate_structured("Test prompt", CandidateProfile)
        assert mock_client.models.generate_content.call_count == 3


# ---------------------------------------------------------------------------
# Retry delay: honouring what the server actually asked for
# ---------------------------------------------------------------------------


def rate_limited(retry_delay: str | None = None, extra_details: list | None = None):
    """A 429 shaped the way Gemini really returns one."""
    details: list = list(extra_details or [])
    if retry_delay is not None:
        details.append(
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}
        )
    return genai_errors.APIError(
        429,
        {
            "error": {
                "code": 429,
                "message": "You exceeded your current quota",
                "status": "RESOURCE_EXHAUSTED",
                "details": details,
            }
        },
    )


def test_server_retry_delay_is_read_from_retry_info():
    assert server_retry_delay(rate_limited("20.138409212s")) == pytest.approx(20.138409212)


def test_server_retry_delay_ignores_unrelated_details():
    error = rate_limited(
        "7s",
        extra_details=[
            {"@type": "type.googleapis.com/google.rpc.Help", "links": [{"url": "https://x"}]},
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": []},
        ],
    )

    assert server_retry_delay(error) == pytest.approx(7.0)


@pytest.mark.parametrize(
    "payload",
    [
        {"error": {"details": []}},
        {"error": {}},
        {},
        {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.Help"}]}},
        {"error": {"details": ["not-a-dict"]}},
        {"error": {"details": [{"@type": ".../RetryInfo", "retryDelay": "not-a-duration"}]}},
    ],
)
def test_server_retry_delay_is_absent_when_the_server_did_not_say(payload):
    assert server_retry_delay(genai_errors.APIError(429, payload)) is None


def test_server_retry_delay_falls_back_to_the_retry_after_header():
    error = genai_errors.APIError(429, {"error": {}})
    error.response = MagicMock(headers={"Retry-After": "12"})

    assert server_retry_delay(error) == pytest.approx(12.0)


def test_server_retry_delay_rejects_a_negative_duration():
    assert server_retry_delay(rate_limited("-5s")) is None


def test_retry_waits_as_long_as_the_server_asked():
    """A short fixed backoff is useless against a per-minute quota."""
    with patch("app.ai.llm.gemini_provider.time.sleep") as mock_sleep:
        operation = MagicMock(side_effect=[rate_limited("11s"), "ok"])

        assert call_with_retry(operation, "unit test") == "ok"
        mock_sleep.assert_called_once_with(pytest.approx(11.0))


def test_a_server_delay_is_capped():
    """One implausible value must not park the request for minutes."""
    with patch("app.ai.llm.gemini_provider.time.sleep") as mock_sleep, patch(
        "app.ai.llm.gemini_provider.GEMINI_TIMEOUT_SECONDS", 600
    ):
        operation = MagicMock(side_effect=[rate_limited("3600s"), "ok"])

        assert call_with_retry(operation, "unit test") == "ok"
        mock_sleep.assert_called_once_with(MAX_RETRY_DELAY_SECONDS)


def test_retry_falls_back_to_exponential_backoff_without_server_advice():
    with patch("app.ai.llm.gemini_provider.time.sleep") as mock_sleep:
        operation = MagicMock(side_effect=[rate_limited(), rate_limited(), "ok"])

        assert call_with_retry(operation, "unit test") == "ok"
        assert [call.args[0] for call in mock_sleep.call_args_list] == [
            RETRY_BACKOFF_SECONDS,
            RETRY_BACKOFF_SECONDS * 2,
        ]


def test_retry_gives_up_when_the_wait_exceeds_the_remaining_budget():
    """Sleeping past the request's own timeout only delays the same failure."""
    with patch("app.ai.llm.gemini_provider.time.sleep") as mock_sleep, patch(
        "app.ai.llm.gemini_provider.GEMINI_TIMEOUT_SECONDS", 5
    ):
        operation = MagicMock(side_effect=rate_limited("20s"))

        with pytest.raises(genai_errors.APIError):
            call_with_retry(operation, "unit test")

        mock_sleep.assert_not_called()
        assert operation.call_count == 1


class FakeClock:
    """A clock that only moves when the code under test sleeps.

    The budget check reads the wall clock, so a mocked sleep that leaves time
    frozen would let the retry loop wait forever for free. Advancing the clock
    by exactly what was slept makes the bound observable and deterministic.
    """

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_retry_never_sleeps_longer_than_the_whole_timeout_allows():
    """Total sleeping is bounded by the timeout however many attempts remain."""
    clock = FakeClock()
    with patch("app.ai.llm.gemini_provider.time.sleep", clock.sleep), patch(
        "app.ai.llm.gemini_provider.time.monotonic", clock.monotonic
    ), patch("app.ai.llm.gemini_provider.GEMINI_TIMEOUT_SECONDS", 10):
        operation = MagicMock(side_effect=rate_limited("6s"))

        with pytest.raises(genai_errors.APIError):
            call_with_retry(operation, "unit test")

        # One 6s wait fits in the 10s budget; a second would not, so the loop
        # stops rather than sleeping past the request's own timeout.
        assert clock.slept == [6.0]
        assert clock.now <= 10
        assert operation.call_count == 2


def test_retry_budget_is_spent_across_attempts_not_reset_each_time():
    clock = FakeClock()
    with patch("app.ai.llm.gemini_provider.time.sleep", clock.sleep), patch(
        "app.ai.llm.gemini_provider.time.monotonic", clock.monotonic
    ), patch("app.ai.llm.gemini_provider.GEMINI_TIMEOUT_SECONDS", 30):
        operation = MagicMock(side_effect=[rate_limited(), rate_limited(), "ok"])

        assert call_with_retry(operation, "unit test") == "ok"
        assert clock.slept == [RETRY_BACKOFF_SECONDS, RETRY_BACKOFF_SECONDS * 2]
        assert clock.now == RETRY_BACKOFF_SECONDS * 3


def test_a_permanent_error_is_never_retried_however_it_is_shaped():
    """A 400 carrying RetryInfo is still a request that will fail identically."""
    with patch("app.ai.llm.gemini_provider.time.sleep") as mock_sleep:
        error = genai_errors.APIError(
            400,
            {
                "error": {
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "1s",
                        }
                    ]
                }
            },
        )
        operation = MagicMock(side_effect=error)

        with pytest.raises(genai_errors.APIError):
            call_with_retry(operation, "unit test")

        assert operation.call_count == 1
        mock_sleep.assert_not_called()
