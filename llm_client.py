#!/usr/bin/env python
import requests
import json
import os

def list_models():
    """List available models from Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model["name"] for model in models]
        return []
    except:
        return []

def send_to_llm(request):
    """Send the request to local Ollama instance and get a response"""
    models = list_models()
    
    # Get model from environment variables or use default
    model = os.getenv("MODEL", "gemma2:latest")
    print(f"Using model: {model}")
    
    # Add system prompt for better voice responses
    system_prompt = "You are a voice chat bot. Answer briefly. Do not use markdown. Do not use <think> tags."
    full_prompt = f"{system_prompt}\n\nUser: {request}"
    
    try:
        # Try the completion API which works well with newer Ollama versions
        url = "http://localhost:11434/api/completion"
        data = {
            "model": model,
            "prompt": full_prompt,
            "stream": False
        }
        
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response received")
            
        # If that doesn't work, try the older generate API
        print("Completion API failed, trying generate API...")
        url = "http://localhost:11434/api/generate"
        response = requests.post(url, json=data)
        if response.status_code == 200:
            try:
                # Get just the first line of the response (first JSON object)
                first_json = response.text.strip().split('\n')[0]
                result = json.loads(first_json)
                return result.get("response", "No response received")
            except:
                # If we can't parse JSON, return the raw text
                return "Received response but couldn't parse it properly"
    
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama API: {e}")
        return "I'm sorry, I had trouble connecting to the local LLM service. Make sure Ollama is running and you have models installed."