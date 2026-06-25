import json
import logging
from .bedrock_client import BedrockClient

class MacroSentinel:
    def __init__(self, events_file, finnhub_token=None, region="us-east-1"):
        self.events_file = events_file
        self.finnhub_token = finnhub_token
        self.region = region
        self.bedrock = None
        if region and region.strip():
            self.bedrock = BedrockClient(region=region)
        else:
            logging.info("MacroSentinel: Bedrock disabled because region is empty")

    def get_mode(self):
        """Retourne un dictionnaire avec le mode et le multiplicateur"""
        return {"mode": "normal", "multiplier": 1.0}

    def analyze(self, event_text):
        if self.bedrock is None:
            logging.warning("Bedrock not available, returning dummy analysis")
            return {"sentiment": "neutral", "confidence": 0.5, "reason": "Bedrock disabled"}
        prompt = f"Analyse the following economic event and give a sentiment score (-1 to 1) and confidence:\n{event_text}"
        response = self.bedrock.invoke_model(
            model_id="anthropic.claude-v2",
            prompt=prompt,
            max_tokens=200
        )
        return response.get("completion", "{}")

    def get_events(self):
        try:
            with open(self.events_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading events file: {e}")
            return []
