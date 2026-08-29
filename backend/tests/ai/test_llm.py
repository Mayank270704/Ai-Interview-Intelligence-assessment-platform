from app.ai.llm.client import LLMClient


def test_gemini_connection():
    client = LLMClient()
    response = client.generate("Reply with exactly: Gemini connection successful")

    assert response.strip() == "Gemini connection successful"