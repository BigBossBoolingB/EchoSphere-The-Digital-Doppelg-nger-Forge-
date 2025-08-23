import logging
import os
import random

import persona_pb2

logger = logging.getLogger(__name__)


class AIClient:
    """
    A client to interact with AI services.
    This is a simulated client that mimics the behavior of a real AI API client.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("AI_PROVIDER_API_KEY")
        if not self.api_key:
            logger.warning("AI_PROVIDER_API_KEY is not set. Running in simulation mode.")

    def get_text_analysis(self, text: str) -> persona_pb2.AnalysisFeatures:
        """
        Simulates AI analysis of the given text.
        """
        logger.info(f"AIClient: Analyzing text: '{text[:30]}...'")
        words = text.lower().split()
        cleaned_words = [word.strip(".,!?;") for word in words]
        keywords = list(set([word for word in cleaned_words if len(word) >= 4]))
        sentiment = (
            "positive"
            if "good" in cleaned_words or "great" in cleaned_words
            else "neutral"
        )

        analysis = persona_pb2.AnalysisFeatures(
            sentiment=sentiment, keywords=keywords, word_count=len(words)
        )
        logger.info(f"AIClient: Analysis complete: {analysis.sentiment}")
        return analysis

    def generate_response(self, persona_doc: dict, prompt: str) -> str:
        """
        Simulates text generation based on persona traits.
        """
        logger.info(f"AIClient: Generating response for prompt: '{prompt}'")
        # In a real scenario, we'd likely use the 'latest_analysis' field
        analysis_data = persona_doc.get("latest_analysis", {})
        sentiment = analysis_data.get("sentiment", "neutral")
        keywords = analysis_data.get("keywords", [])

        if not keywords:
            return (
                f"As a persona with a {sentiment} outlook, I don't have much to say "
                f"about '{prompt}' yet."
            )

        chosen_keyword = random.choice(keywords)

        if sentiment == "positive":
            return (
                f"I feel great about '{prompt}'! It reminds me of the importance of "
                f"{chosen_keyword}."
            )
        else:
            return (
                f"When considering '{prompt}', it's important to think about "
                f"{chosen_keyword}."
            )
