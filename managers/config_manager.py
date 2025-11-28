import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        # Load environment variables (override existing ones)
        load_dotenv(override=True)
        
        # Load config.json
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
    
    def get_api_key(self, provider: str) -> str:
        """Get API key from environment variables"""
        if provider == "openrouter":
            return os.getenv("OPENROUTER_API_KEY", "")
        elif provider == "google":
            return os.getenv("GOOGLE_API_KEY", "")
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def get_llm_config(self, use_case: str) -> Dict[str, Any]:
        """Get LLM configuration for a specific use case"""
        if use_case not in self.config["llm_models"]:
            raise ValueError(f"Unknown use case: {use_case}")
        
        return self.config["llm_models"][use_case]
    
    def get_api_endpoint(self, provider: str) -> str:
        """Get API endpoint for a provider"""
        if provider not in self.config["api_endpoints"]:
            raise ValueError(f"Unknown provider: {provider}")
        
        return self.config["api_endpoints"][provider]
    
    def update_model(self, use_case: str, model: str):
        """Update the model for a specific use case"""
        if use_case in self.config["llm_models"]:
            self.config["llm_models"][use_case]["model"] = model
            # Save back to config.json
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=2)

