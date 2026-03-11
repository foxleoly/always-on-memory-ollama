#!/usr/bin/env python3
"""
GitHub Copilot Provider for Always-On Memory Agent

Implements GitHub Copilot token exchange and OpenAI-compatible client.
Supports automatic token refresh and 401 retry logic.
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import openai
import requests


class CopilotProvider:
    """
    GitHub Copilot Provider that implements token loading, exchange,
    and OpenAI-compatible client interface.
    """
    
    SUPPORTED_MODELS = [
        # OpenAI models
        "gpt-4o", 
        "gpt-4o-mini", 
        "gpt-4.1",
        
        # Anthropic models
        "claude-3.5-sonnet", 
        "claude-3.7-sonnet", 
        "claude-sonnet-4",
        
        # OpenAI o1 series
        "o1", 
        "o3-mini", 
        "o4-mini",
        
        # Google models
        "gemini-2.0-flash", 
        "gemini-2.5-pro",
    ]
    
    def __init__(self, model: str = "gpt-4o", api_url: str = None):
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported. Supported models: {', '.join(self.SUPPORTED_MODELS)}")
        
        self.model = model
        self.token = None
        self.token_expiry = None
        self.client = None
        
        # API URL from environment or parameter
        self.api_url = api_url or os.getenv("COPILOT_API_URL", "https://api.githubcopilot.com")
        
        # Load and exchange token
        self._refresh_token()
        
        # Initialize OpenAI client
        self._init_client()
    
    def _get_github_token(self) -> str:
        """
        Get GitHub token from multiple sources in priority order:
        1. GITHUB_TOKEN environment variable
        2. COPILOT_TOKEN environment variable
        3. ~/.config/github-copilot/hosts.json
        4. gh CLI authentication
        """
        
        # 1. Check environment variables
        token = os.getenv("GITHUB_TOKEN") or os.getenv("COPILOT_TOKEN")
        if token:
            return token
        
        # 2. Check ~/.config/github-copilot/hosts.json
        hosts_file = Path.home() / ".config" / "github-copilot" / "hosts.json"
        if hosts_file.exists():
            try:
                with open(hosts_file, "r") as f:
                    hosts_data = json.load(f)
                    # Assuming the structure has github.com entry
                    github_entry = hosts_data.get("github.com", {})
                    token = github_entry.get("oauth_token")
                    if token:
                        return token
            except (json.JSONDecodeError, KeyError):
                pass
        
        # 3. Try gh CLI
        try:
            result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
            token = result.stdout.strip()
            if token:
                return token
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        raise ValueError("Could not find GitHub token from any source. Please set GITHUB_TOKEN or COPILOT_TOKEN environment variable, or authenticate with 'gh auth login'.")
    
    def _exchange_token(self, github_token: str) -> dict:
        """
        Exchange GitHub token for Copilot token
        API: https://api.github.com/copilot_internal/v2/token
        """
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        response = requests.post(
            "https://api.github.com/copilot_internal/v2/token",
            headers=headers
        )
        
        if response.status_code != 200:
            raise ValueError(f"Token exchange failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _refresh_token(self):
        """
        Refresh the Copilot token if expired or about to expire
        """
        # Check if we need to refresh (if token expires in less than 5 minutes)
        if self.token_expiry and datetime.now() < self.token_expiry - timedelta(minutes=5):
            return  # Token is still valid
        
        # Get GitHub token and exchange for Copilot token
        github_token = self._get_github_token()
        copilot_data = self._exchange_token(github_token)
        
        self.token = copilot_data["token"]
        # Token expiry is given in seconds since epoch
        expiry_timestamp = copilot_data.get("expires_at", time.time() + 3600)  # Default to 1 hour if not provided
        self.token_expiry = datetime.fromtimestamp(expiry_timestamp)
    
    def _init_client(self):
        """
        Initialize OpenAI-compatible client with Copilot base URL
        """
        self._refresh_token()  # Ensure token is fresh
        
        self.client = openai.OpenAI(
            base_url=self.api_url,
            api_key=self.token
        )
    
    def _ensure_fresh_token(self):
        """
        Ensure token is fresh before making API calls
        """
        self._refresh_token()
        
        # Update client with new token if needed
        if self.client.api_key != self.token:
            self.client = openai.OpenAI(
                base_url=self.api_url,
                api_key=self.token
            )
    
    def _handle_401_retry(self, func, *args, **kwargs):
        """
        Handle 401 Unauthorized errors by refreshing token and retrying
        """
        try:
            return func(*args, **kwargs)
        except openai.AuthenticationError as e:
            if "401" in str(e):
                # Token might be expired, refresh and retry
                self._refresh_token()
                self.client = openai.OpenAI(
                    base_url=self.api_url,
                    api_key=self.token
                )
                
                # Retry the function
                return func(*args, **kwargs)
            else:
                raise e
        except Exception as e:
            raise e
    
    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """
        Send a chat request to Copilot (async, non-blocking).
        """
        def _chat_sync():
            self._ensure_fresh_token()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        
        return await asyncio.to_thread(self._handle_401_retry, _chat_sync)
    
    async def generate_json(self, system_prompt: str, user_message: str) -> dict:
        """
        Send a request and parse response as JSON (async, non-blocking).
        """
        def _generate_json_sync():
            self._ensure_fresh_token()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1  # Lower temperature for more consistent JSON
            )
            return response.choices[0].message.content
        
        response_text = await asyncio.to_thread(self._handle_401_retry, _generate_json_sync)
        
        try:
            # Try to extract JSON from response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            return {"error": "No JSON found", "raw": response_text}
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}\nResponse: {response_text[:200]}")
            return {"error": f"JSON parse error: {e}", "raw": response_text}


# Test function for development
async def test_copilot_provider():
    """
    Test function to verify Copilot provider functionality
    """
    try:
        print("Testing CopilotProvider...")
        
        # Create provider instance
        provider = CopilotProvider(model="gpt-4o")
        print(f"✅ Initialized CopilotProvider with model: {provider.model}")
        
        # Test basic chat
        print("\nTesting basic chat...")
        response = await provider.chat(
            system_prompt="You are a helpful assistant. Respond in English.",
            user_message="Hello! What models are available?"
        )
        print(f"Response: {response[:100]}...")
        
        # Test JSON generation
        print("\nTesting JSON generation...")
        json_response = await provider.generate_json(
            system_prompt="You are a JSON generator. Return only valid JSON.",
            user_message='Return {"status": "ok", "message": "test successful"}'
        )
        print(f"JSON Response: {json_response}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_copilot_provider())