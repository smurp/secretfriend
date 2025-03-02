#!/usr/bin/env python
import subprocess
import re
import os

def clean_response(text):
    """Remove any <think> tags and their contents from the response"""
    # Remove <think>...</think> blocks
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove any other XML/HTML-like tags
    cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
    return cleaned_text.strip()

def speak(text, sound_listener=None):
    """Use macOS 'say' command to speak text aloud and set the spoken text for echo detection"""
    cleaned_text = clean_response(text)
    print(f"Speaking: {cleaned_text}")
    
    # Record what is being spoken for echo detection
    if sound_listener:
        sound_listener.set_last_spoken(cleaned_text)
    
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