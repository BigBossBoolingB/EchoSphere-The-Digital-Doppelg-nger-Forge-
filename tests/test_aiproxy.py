import pytest
from echosystem.aiproxy.client import AIClient
import persona_pb2

def test_get_text_analysis():
    """
    Tests the simulation logic for text analysis.
    """
    client = AIClient(api_key="test_key")
    text = "This is a great, high-quality test."

    result = client.get_text_analysis(text)

    assert isinstance(result, persona_pb2.AnalysisFeatures)
    assert result.sentiment == "positive"
    assert "great" in result.keywords
    assert "high-quality" in result.keywords
    assert "test" in result.keywords
    assert result.word_count == 6

def test_generate_response_positive():
    """
    Tests the simulation logic for text generation with a positive persona.
    """
    client = AIClient(api_key="test_key")
    persona_doc = {
        "latest_analysis": {
            "sentiment": "positive",
            "keywords": ["quality", "software"]
        }
    }
    prompt = "your work"

    result = client.generate_response(persona_doc, prompt)

    assert "great" in result
    assert "your work" in result
    keyword_present = any(kw in result for kw in persona_doc["latest_analysis"]["keywords"])
    assert keyword_present

def test_generate_response_neutral():
    """
    Tests the simulation logic for text generation with a neutral persona.
    """
    client = AIClient(api_key="test_key")
    persona_doc = {
        "latest_analysis": {
            "sentiment": "neutral",
            "keywords": ["system", "data"]
        }
    }
    prompt = "the future"

    result = client.generate_response(persona_doc, prompt)

    assert "considering" in result
    assert "the future" in result
    keyword_present = any(kw in result for kw in persona_doc["latest_analysis"]["keywords"])
    assert keyword_present
