import requests
import json
import sys
import os
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managers.config_manager import ConfigManager

class OpenRouterClient:
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path=config_path) if config_path else ConfigManager()
        self.headers = {
            "Authorization": f"Bearer {self.config_manager.get_api_key('openrouter')}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://openrouter.ai/api/v1"
        
    def generate(self, prompt: str, use_case: str = "question_generator", 
                system_prompt: Optional[str] = None) -> str:
        """Generate response using OpenRouter API"""
        
        # Get configuration
        config = self.config_manager.get_llm_config(use_case)
        api_key = self.config_manager.get_api_key("openrouter")
        endpoint = self.config_manager.get_api_endpoint("openrouter")
        
        if not api_key:
            raise ValueError("OpenRouter API key not found in .env file")
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-tutor-dash",  # Optional
            "X-Title": "AI Tutor DASH System"  # Optional
        }
        
        data = {
            "model": config["model"],
            "messages": messages,
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 1000)
        }
        
        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenRouter API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise
        except KeyError as e:
            print(f"Unexpected response format: {e}")
            print(f"Response: {response.text}")
            raise
    
    def generate_batch(self, prompts: List[str], use_case: str = "question_generator",
                      system_prompt: Optional[str] = None) -> List[str]:
        """Generate multiple responses (calls API sequentially)"""
        responses = []
        for prompt in prompts:
            try:
                response = self.generate(prompt, use_case, system_prompt)
                responses.append(response)
            except Exception as e:
                print(f"Error generating response for prompt: {e}")
                responses.append("")
        
        return responses