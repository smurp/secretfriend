#!/usr/bin/env python
import requests
import json
import os
import subprocess
import re

def clean_response(text):
    """Remove any <think> tags and their contents from the response"""
    # Remove <think>...</think> blocks
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove any other XML/HTML-like tags
    cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
    return cleaned_text.strip()

def speak(text):
    """Use macOS 'say' command to speak text aloud"""
    cleaned_text = clean_response(text)
    print(f"Speaking: {cleaned_text}")
    
    # Force text to be non-empty and properly escaped
    if cleaned_text.strip():
        # Use subprocess.run with shell=False and properly escape the text
        try:
            subprocess.run(["say", cleaned_text], check=True)
            print("Speech completed successfully")
        except subprocess.SubprocessError as e:
            print(f"Error with speech synthesis: {e}")
            # Fallback approach
            try:
                # Simple fallback with no special escaping
                os.system('say "' + cleaned_text.replace('"', '\\"') + '"')
                print("Speech completed using fallback method")
            except Exception as e:
                print(f"Failed to speak even with fallback: {e}")
    else:
        print("Nothing to speak (empty response)")



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
    
    # Use gemma2:latest as the default model
    model = "gemma2:latest"
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

def main():
    print("Secret Friend is active.")
    print("Type your questions and press Enter. I'll speak the responses.")
    print("Type 'exit' to quit.")
    
    # List available models at startup
    models = list_models()
    if models:
        print(f"Available models: {models}")
    else:
        print("No models found. Make sure Ollama is running and you have models installed.")
    
    while True:
        user_input = input("> ").strip()
        
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        
        if user_input:
            print(f"Sending to LLM: '{user_input}'")
            response = send_to_llm(user_input)
            print(f"Original response: {response}")
            speak(response)

if __name__ == "__main__":
    main()