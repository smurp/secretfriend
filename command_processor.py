#!/usr/bin/env python
import os
import sys
from llm_client import list_models

def process_command(command):
    """Process a command and check if it's a special system command"""
    # Get the pre and post command phrases from environment
    pre_command = os.getenv("PRE_COMMAND", "hocus pocus").lower()
    post_command = os.getenv("POST_COMMAND", "abracadabra").lower()
    
    # Check if the command starts with pre_command and ends with post_command
    command = command.lower().strip()
    
    if pre_command in command and post_command in command:
        # Extract the actual command between pre and post commands
        start_idx = command.find(pre_command) + len(pre_command)
        end_idx = command.find(post_command, start_idx)
        
        if end_idx > start_idx:
            actual_command = command[start_idx:end_idx].strip()
            print(f"Special command detected: '{actual_command}'")
            
            # Process known special commands
            if actual_command == "list models":
                models = list_models()
                if models:
                    return f"Available models: {', '.join(models)}"
                else:
                    return "No Ollama models found. Make sure Ollama is running with models installed."
            
            elif actual_command == "exit":
                print("Exit command received. Goodbye!")
                sys.exit(0)
                
            # Add more special commands here as needed
            # elif actual_command == "some other command":
            #     return do_something()
            
            else:
                return f"Unknown command: {actual_command}. Try 'list models' or 'exit'."
                
    # Not a special command, return None to process normally with LLM
    return None