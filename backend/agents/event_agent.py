from llm_client import LLMClient
import json

class EventIntelligenceAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.system_prompt = (
            "You are an Event Intelligence Agent for a Global Supply Chain Digital Twin. "
            "Your task is to analyze news feeds, weather advisories, and trade notifications, "
            "and extract structured disruption events. You must output ONLY a valid JSON object."
        )

    def analyze_disruption(self, text: str) -> dict:
        """
        Parses text and returns structured disruption details.
        """
        prompt = f"""
        Analyze the following text and extract the disruption details.
        
        Text: "{text}"
        
        Return a JSON object with the following fields:
        1. "event": Type of event (e.g., Typhoon, War, Port Closure, Tariff, Strike, Commodity Price Spike).
        2. "location": Affected country, city, or ocean region (e.g., Taiwan, Red Sea, Shanghai Port).
        3. "severity": "Low", "Medium", "High", or "Critical".
        4. "industry": Primary industry affected (e.g., Semiconductors, Batteries, General Logistics).
        5. "expected_duration_days": Estimated duration in days as an integer (convert e.g., "5 days" to 5, "one week" to 7, "unknown" to 30).
        6. "description": A concise summary of the disruption.
        
        JSON:
        """
        result = self.llm.generate_json(prompt, system_instruction=self.system_prompt)
        
        # Post-process safety defaults
        if "error" in result:
            return {
                "event": "Disruption Alert",
                "location": "Global",
                "severity": "Medium",
                "industry": "Logistics",
                "expected_duration_days": 10,
                "description": text[:200]
            }
        
        return result
