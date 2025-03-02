#!/usr/bin/env python
import os
from llm_client import list_models, send_to_llm
from speech_output import speak
from command_processor import process_command

def cli_mode():
    """Run the application in command-line interface mode"""
    print("Secret Friend is active in CLI mode.")
    print("Type your questions and press Enter. I'll speak the responses.")
    print("Special commands: Surround system commands with PRE_COMMAND and POST_COMMAND")
    print(f"  Example: {os.getenv('PRE_COMMAND', 'hocus pocus')} list models {os.getenv('POST_COMMAND', 'abracadabra')}")
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
            # Check if it's a special command
            special_response = process_command(user_input)
            if special_response:
                print(special_response)
                speak(special_response)
            else:
                # Regular LLM processing
                print(f"Sending to LLM: '{user_input}'")
                response = send_to_llm(user_input)
                print(f"Original response: {response}")
                speak(response)

def cli_mode_with_initial_text(initial_text):
    """Run CLI mode with an initial query and continue in interactive mode"""
    print("Secret Friend is active in CLI mode with initial query.")
    
    # Process the initial text
    if initial_text:
        # Check if it's a special command
        special_response = process_command(initial_text)
        if special_response:
            print(special_response)
            speak(special_response)
        else:
            # Regular LLM processing
            print(f"Sending to LLM: '{initial_text}'")
            response = send_to_llm(initial_text)
            print(f"Original response: {response}")
            speak(response)
    
    # Then continue with normal CLI mode
    cli_mode()