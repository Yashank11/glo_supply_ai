import os
import json
import re
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

class LLMClient:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.mistral_key = os.getenv("MISTRAL_API_KEY")
        
        self.gemini_model = "gemini-3.1-flash-lite"
        self.groq_model = "llama-3.3-70b-specdec"
        self.openrouter_model = "meta-llama/llama-3.3-70b-instruct"
        self.mistral_model = "mistral-small-latest"
        
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
        else:
            print("[WARNING] GEMINI_API_KEY missing. Gemini operations will fail.")

    def generate_text(self, prompt: str, system_instruction: str = None) -> str:
        """
        Executes text generation trying Gemini first, falling back to Groq, OpenRouter, and Mistral.
        """
        # 1. Try Gemini
        if self.gemini_key:
            try:
                model = genai.GenerativeModel(
                    model_name=self.gemini_model,
                    system_instruction=system_instruction
                )
                response = model.generate_content(prompt)
                if response.text:
                    return response.text
            except Exception as e:
                print(f"[FALLBACK] Gemini failed: {e}. Trying Groq...")

        # 2. Try Groq
        if self.groq_key:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                }
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": self.groq_model,
                    "messages": messages
                }
                
                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[FALLBACK] Groq API returned status {res.status_code}. Trying OpenRouter...")
            except Exception as e:
                print(f"[FALLBACK] Groq call failed: {e}. Trying OpenRouter...")

        # 3. Try OpenRouter
        if self.openrouter_key:
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost:8000",
                    "X-Title": "Supply Chain Digital Twin"
                }
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": self.openrouter_model,
                    "messages": messages
                }
                
                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[FALLBACK] OpenRouter returned status {res.status_code}. Trying Mistral...")
            except Exception as e:
                print(f"[FALLBACK] OpenRouter failed: {e}. Trying Mistral...")

        # 4. Try Mistral
        if self.mistral_key:
            try:
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.mistral_key}",
                    "Content-Type": "application/json"
                }
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": self.mistral_model,
                    "messages": messages
                }
                
                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[ERROR] Mistral also failed: {e}")

        return "Error: All AI model connections (Gemini, Groq, OpenRouter, Mistral) failed. Please check network connectivity and API keys."

    def generate_json(self, prompt: str, system_instruction: str = None) -> dict:
        """
        Executes JSON generation with fallback routing across the models.
        """
        # Append clear instructions to force JSON formatting for fallback compatibility
        json_prompt = prompt + "\n\nIMPORTANT: Return ONLY a valid JSON object. Do not include markdown wraps or trailing text."
        
        # 1. Try Gemini
        if self.gemini_key:
            try:
                model = genai.GenerativeModel(
                    model_name=self.gemini_model,
                    system_instruction=system_instruction
                )
                config = genai.types.GenerationConfig(response_mime_type="application/json")
                response = model.generate_content(prompt, generation_config=config)
                return self._parse_json_text(response.text)
            except Exception as e:
                print(f"[FALLBACK] Gemini JSON failed: {e}. Trying Groq...")

        # If Gemini fails, use generate_text fallback chain and manually extract JSON
        raw_text_response = self.generate_text(json_prompt, system_instruction)
        try:
            return self._parse_json_text(raw_text_response)
        except Exception as e:
            # Last-ditch manual regex extract
            match = re.search(r"(\{.*\})", raw_text_response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return {"error": "Failed to parse JSON response from LLM.", "raw_response": raw_text_response[:300]}

    def _parse_json_text(self, text: str) -> dict:
        """
        Helper to clean up markdown fences and load JSON.
        """
        clean_text = text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n", "", clean_text)
            clean_text = re.sub(r"\n```$", "", clean_text)
            clean_text = clean_text.strip()
        return json.loads(clean_text)
