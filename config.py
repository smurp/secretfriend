#!/usr/bin/env python
"""
Configuration module for Secret Friend.
Loads and manages environment variables and settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv(dotenv_path='.env', override=True)

# Define default values for configuration
DEFAULT_CONFIG = {
    "MODEL": "gemma2:latest",
    "VOSK_MODEL_PATH": "vosk-model-small-en-us-0.15",
    "HI_PHRASE": "listen up",
    "GO_PHRASE": "go for it", 
    "DONE_PHRASE": "that will do",
    "PRE_COMMAND": "hocus pocus",
    "POST_COMMAND": "abracadabra",
    "COMMAND_TIMEOUT": "30",
    "SILENCE_TIMEOUT": "5"
}

def get_config(key, default=None):
    """Get a configuration value from environment variables with fallback to defaults"""
    # Use the provided default or get it from the DEFAULT_CONFIG
    if default is None and key in DEFAULT_CONFIG:
        default = DEFAULT_CONFIG[key]
        
    return os.getenv(key, default)

def set_config(key, value):
    """Set a configuration value as an environment variable"""
    os.environ[key] = str(value)

def print_config():
    """Print the current configuration values"""
    print("Current Configuration:")
    for key in DEFAULT_CONFIG.keys():
        print(f"  {key} = '{get_config(key)}'")