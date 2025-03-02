#!/usr/bin/env python
"""
Secret Friend - Voice or CLI interaction with local LLMs
"""
import sys
import os
import argparse

# Import configuration module (also loads environment variables)
from config import get_config, set_config, print_config

# Try to import voice recognition module
try:
    from sound_listener import VOICE_AVAILABLE
except ImportError:
    VOICE_AVAILABLE = False

# Import other modules
from llm_client import list_models, send_to_llm
from speech_output import speak
from command_processor import process_command
from cli_mode import cli_mode, cli_mode_with_initial_text

def show_help():
    """Display custom help message with current settings"""
    # Get current settings
    current_hi_phrase = get_config("HI_PHRASE")
    current_go_phrase = get_config("GO_PHRASE")
    current_done_phrase = get_config("DONE_PHRASE")
    current_pre_command = get_config("PRE_COMMAND")
    current_post_command = get_config("POST_COMMAND")

    # Display help message
    print("Secret Friend - Voice or CLI interaction with local LLMs")
    print("\nUsage examples:")
    print("  ./secretfriend.py                    # Start in voice mode")
    print("  ./secretfriend.py --cli              # Start in CLI mode")
    print("  ./secretfriend.py --command 'list models'  # Execute command directly")
    print("  ./secretfriend.py tell me a joke     # Send text to LLM and exit")
    print("  ./secretfriend.py --cli tell me a joke  # Process query and stay in CLI mode")
    print("  ./secretfriend.py --hi 'hey you' --go 'off you go'  # Set custom phrases")
    print("\nOptions:")
    print("  -h, --help                 Show this help message and exit")
    print("  --cli                      Run in command-line interface mode")
    print("  --model-path PATH          Path to Vosk speech recognition model")
    print("  --command COMMAND          Execute a specific command directly and exit")
    print("  --hi PHRASE                Set the wake phrase (HI_PHRASE)")
    print("  --go PHRASE                Set the end phrase (GO_PHRASE)")
    print("  --done PHRASE              Set the conversation exit phrase (DONE_PHRASE)")
    print("  text...                    Text to send directly to the LLM")
    print("\nCurrent Settings:")
    print(f"  HI_PHRASE = '{current_hi_phrase}'")
    print(f"  GO_PHRASE = '{current_go_phrase}'")
    print(f"  DONE_PHRASE = '{current_done_phrase}'")
    print(f"  PRE_COMMAND = '{current_pre_command}'")
    print(f"  POST_COMMAND = '{current_post_command}'")
    print("\nSpecial Commands:")
    print(f"  {current_pre_command} list models {current_post_command}")
    print(f"  {current_pre_command} exit {current_post_command}")

def main():
    """Main entry point for Secret Friend application"""
    # Check for help flags before creating the parser
    if "-h" in sys.argv or "--help" in sys.argv:
        show_help()
        return

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Secret Friend - Voice or CLI interaction with local LLMs", add_help=False)
    parser.add_argument("--cli", action="store_true", help="Run in command-line interface mode")
    parser.add_argument("--model-path", help="Path to Vosk speech recognition model")
    parser.add_argument("--command", help="Execute a specific command directly and exit")
    parser.add_argument("--hi", help="Set the wake phrase (HI_PHRASE)")
    parser.add_argument("--go", help="Set the end phrase (GO_PHRASE)")
    parser.add_argument("--done", help="Set the conversation exit phrase (DONE_PHRASE)")
    parser.add_argument("text", nargs="*", help="Text to send directly to the LLM")
    
    args = parser.parse_args()
    
    # Set environment variables from command line arguments
    if args.model_path:
        set_config("VOSK_MODEL_PATH", args.model_path)
    if args.hi:
        set_config("HI_PHRASE", args.hi)
    if args.go:
        set_config("GO_PHRASE", args.go)
    if args.done:
        set_config("DONE_PHRASE", args.done)
    
    # Handle direct command execution
    if args.command:
        print(f"Executing command: {args.command}")
        if args.command == "list models":
            models = list_models()
            if models:
                print(f"Available models: {', '.join(models)}")
            else:
                print("No models found. Make sure Ollama is running and you have models installed.")
        # Add more direct commands as needed
        # elif args.command == "another_command":
        #     do_something()
        else:
            print(f"Unknown command: {args.command}")
        return
    
    # Handle direct LLM query
    if args.text and not args.cli:
        query = " ".join(args.text)
        print(f"Sending to LLM: '{query}'")
        response = send_to_llm(query)
        print(f"Response: {response}")
        speak(response)
        return
    
    # Normal operation modes
    if args.cli or not VOICE_AVAILABLE:
        if args.text:
            # CLI mode with initial query
            cli_mode_with_initial_text(" ".join(args.text))
        else:
            # Standard CLI mode
            cli_mode()
    else:
        try:
            # Import voice_mode only when needed to avoid circular imports
            from voice_mode import voice_mode
            voice_mode()
        except Exception as e:
            print(f"Error initializing voice mode: {e}")
            print("Falling back to CLI mode...")
            cli_mode()

if __name__ == "__main__":
    main()