#!/usr/bin/env python
import os
from llm_client import list_models, send_to_llm
from speech_output import speak
from command_processor import process_command
from sound_listener import listen_for_wake_word, listen_for_command, SoundDeviceListener

def voice_mode():
    """Run the application in voice-activated mode"""
    # Get wake phrase from environment
    hi_phrase = os.getenv("HI_PHRASE", "listen up").lower()
    go_phrase = os.getenv("GO_PHRASE", "go for it").lower()
    pre_command = os.getenv("PRE_COMMAND", "hocus pocus").lower()
    post_command = os.getenv("POST_COMMAND", "abracadabra").lower()
    done_phrase = os.getenv("DONE_PHRASE", "that will do").lower()
    
    # Get timeout settings
    command_timeout = int(os.getenv("COMMAND_TIMEOUT", "30"))
    silence_timeout = int(os.getenv("SILENCE_TIMEOUT", "5"))
    
    print("Secret Friend is active in voice mode.")
    print(f"Say '{hi_phrase}' to activate, then speak your question, and say '{go_phrase}' when done.")
    print(f"The wake phrase can be changed using the HI_PHRASE environment variable.")
    print(f"The end phrase can be changed using the GO_PHRASE environment variable.")
    print(f"Say '{done_phrase}' at any time to exit the conversation.")
    print(f"Special commands: {pre_command} [command] {post_command}")
    print(f"  Example: {pre_command} list models {post_command}")
    print("Press Ctrl+C to exit.")
    
    # List available models at startup
    models = list_models()
    if models:
        print(f"Available models: {models}")
    else:
        print("No models found. Make sure Ollama is running and you have models installed.")
    
    # Get model path from environment or use default
    model_path = os.getenv("VOSK_MODEL_PATH", "vosk-model-small-en-us-0.15")
    
    # Check if the model exists
    if not os.path.exists(model_path):
        print(f"Vosk model not found at {model_path}")
        print("Please download a model from https://alphacephei.com/vosk/models")
        print("Example: wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print("         unzip vosk-model-small-en-us-0.15.zip")
        print("Or set VOSK_MODEL_PATH to point to your model directory")
        print("Falling back to CLI mode...")
        from cli_mode import cli_mode
        cli_mode()
        return
    
    # Initialize the sound device listener
    try:
        sound_listener = SoundDeviceListener(model_path)
        
        try:
            # Flag to track if we're in an active conversation
            in_conversation = False
            
            while True:
                # If not in a conversation, wait for wake word
                if not in_conversation:
                    if listen_for_wake_word(sound_listener, hi_phrase):
                        in_conversation = True
                
                # If in a conversation or wake word detected, get command
                if in_conversation:
                    # Acknowledge the wake word or ready for next command
                    speak("yes", sound_listener)
                    
                    # Get command
                    command = listen_for_command(sound_listener, go_phrase, command_timeout, silence_timeout)
                    
                    # Check if the done phrase was said
                    if done_phrase in command.lower():
                        print(f"Done phrase '{done_phrase}' detected. Exiting conversation.")
                        speak("Goodbye!", sound_listener)
                        in_conversation = False
                        continue
                    
                    if command:
                        # Check if it's a special command
                        special_response = process_command(command)
                        if special_response:
                            print(special_response)
                            speak(special_response, sound_listener)
                        else:
                            # Regular LLM processing
                            print(f"Sending to LLM: '{command}'")
                            response = send_to_llm(command)
                            print(f"Original response: {response}")
                            speak(response, sound_listener)
                        
                        # After speaking, we remain in conversation mode
                        # No need to wait for the wake word again
                        print(f"Ready for next command. Say '{go_phrase}' after speaking or '{done_phrase}' to exit.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
        finally:
            sound_listener.stop_listening()
    except Exception as e:
        print(f"Error initializing voice recognition: {e}")
        print("Falling back to CLI mode...")
        from cli_mode import cli_mode
        cli_mode()