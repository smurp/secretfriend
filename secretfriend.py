#!/usr/bin/env python
import requests
import json
import os
import subprocess
import re
import sys
import argparse
import time
import queue
import threading
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv(dotenv_path='.env', override=True)

# Set up a flag to track if voice mode is available
VOICE_MODE_AVAILABLE = False

# Try to import voice recognition modules
try:
    import vosk
    import sounddevice as sd
    VOICE_MODE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Voice recognition modules couldn't be imported: {e}")
    print("Voice mode will not be available. Using CLI mode only.")
    VOICE_MODE_AVAILABLE = False

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

class SoundDeviceListener:
    """Class for managing Vosk-based speech recognition with sounddevice"""
    def __init__(self, model_path):
        self.model = vosk.Model(model_path)
        self.sample_rate = 16000
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.listening_thread = None
        self.last_spoken_text = None  # Track the last text spoken by the system
        
        # Debug information about available devices
        print("Available audio devices:")
        print(sd.query_devices())
        print(f"Default input device: {sd.default.device[0]}")
        
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream - add data to queue"""
        if status:
            print(f"Audio status: {status}")
        # Convert float to int16
        audio_data = (indata * 32767).astype(np.int16).tobytes()
        self.audio_queue.put(audio_data)
        
    def start_listening(self):
        """Start the audio stream"""
        if self.is_listening:
            return
            
        self.is_listening = True
        try:
            # Clear the audio queue before starting
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get(False)
                except queue.Empty:
                    break
                
            self.stream = sd.InputStream(
                callback=self._audio_callback,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype='float32'
            )
            self.stream.start()
            print("Audio stream started")
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.is_listening = False
            raise
        
    def stop_listening(self):
        """Stop the audio stream"""
        if not self.is_listening:
            return
            
        self.is_listening = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        print("Audio stream stopped")
        
    def set_last_spoken(self, text):
        """Set the last text spoken by the system"""
        # Convert to lowercase and remove punctuation for easier comparison
        if text:
            self.last_spoken_text = text.lower().strip().replace('.', '').replace('?', '').replace('!', '')
            print(f"Set last spoken text: '{self.last_spoken_text}'")
        
    def should_ignore_text(self, text):
        """Check if recognized text matches what the system just said"""
        if not self.last_spoken_text or not text:
            return False
            
        # Clean up the recognized text
        clean_text = text.lower().strip().replace('.', '').replace('?', '').replace('!', '')
        
        # Check if the recognized text contains the last spoken text
        similarity = self._text_similarity(clean_text, self.last_spoken_text)
        if similarity > 0.7:  # If 70% similar or more, likely hearing the system's speech
            print(f"Ignoring echo detection (similarity: {similarity:.2f}): '{clean_text}'")
            return True
            
        return False
        
    def _text_similarity(self, text1, text2):
        """Calculate similarity between two texts"""
        # Simple similarity check - percent of shorter text in longer text
        if not text1 or not text2:
            return 0
            
        text1, text2 = text1.lower(), text2.lower()
        shorter = text1 if len(text1) < len(text2) else text2
        longer = text2 if len(text1) < len(text2) else text1
        
        # Check if shorter text is contained in longer text
        if shorter in longer:
            return 1.0
            
        # Check for word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0
            
        common_words = words1.intersection(words2)
        return len(common_words) / min(len(words1), len(words2))
    
    def listen_for_phrase(self, timeout=None):
        """Listen for a complete phrase with timeout"""
        rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
        rec.SetWords(True)  # Enable word timestamps
        
        # Start listening if not already
        was_not_listening = not self.is_listening
        if was_not_listening:
            self.start_listening()
            
        text = ""
        start_time = time.time()
        
        try:
            while timeout is None or (time.time() - start_time) < timeout:
                try:
                    data = self.audio_queue.get(block=True, timeout=0.5)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if result.get("text", "").strip():
                            text = result.get("text", "").strip()
                            print(f"Recognized: {text}")
                            
                            # Check if this is likely an echo of what the system just said
                            if self.should_ignore_text(text):
                                print("Ignoring system echo, continuing to listen...")
                                text = ""  # Reset text so we keep listening
                                continue
                            
                            return text
                    else:
                        # Check partial results too
                        partial = json.loads(rec.PartialResult())
                        partial_text = partial.get("partial", "").strip()
                        if partial_text:
                            print(f"Partial: {partial_text}")
                            
                            # Check partial results for echo too
                            if self.should_ignore_text(partial_text):
                                print("Ignoring system echo in partial result...")
                except queue.Empty:
                    pass
                            
            # If we reach here, we've timed out
            print("Recognition timed out")
            
            # Check for any final partial results before giving up
            partial = json.loads(rec.PartialResult())
            partial_text = partial.get("partial", "").strip()
            if partial_text:
                print(f"Final partial: {partial_text}")
                
                # Check if final partial is an echo
                if not self.should_ignore_text(partial_text):
                    return partial_text
                else:
                    print("Ignoring system echo in final partial result")
                
            return ""
        finally:
            # If we weren't listening before, stop listening
            if was_not_listening:
                self.stop_listening()

def listen_for_wake_word(sound_listener, wake_phrase=None):
    """Listen continuously for the wake word using Vosk with improved detection"""
    if wake_phrase is None:
        wake_phrase = os.getenv("HI_PHRASE", "listen up").lower()
        
    print(f"Listening for wake phrase: '{wake_phrase}'...")
    
    # Generate alternative wake word forms
    wake_words = [wake_phrase]
    
    # Split main wake phrase into words and add variations
    words = wake_phrase.split()
    if len(words) > 1:
        # Add partial matches (first word, last word, etc.)
        wake_words.append(words[0])
        wake_words.append(words[-1])
        if len(words) > 2:
            wake_words.append(' '.join(words[:2]))
            wake_words.append(' '.join(words[-2:]))
            
    print(f"Will listen for these variations: {wake_words}")
    
    # Start the listener if not already listening
    sound_listener.start_listening()
    
    # Create partial recognizer to handle partial results
    rec = vosk.KaldiRecognizer(sound_listener.model, sound_listener.sample_rate)
    rec.SetWords(True)  # Enable word timestamps
    
    while True:
        try:
            data = sound_listener.audio_queue.get(block=True, timeout=0.5)
            
            # Check for partial recognition results
            if rec.AcceptWaveform(data):
                # Full result
                result = json.loads(rec.Result())
                text = result.get("text", "").lower().strip()
                print(f"Heard: {text}")
                
                # Check if any wake word variant is in the text
                if any(word in text for word in wake_words):
                    print("Wake word detected in full result!")
                    return True
            else:
                # Partial result
                partial = json.loads(rec.PartialResult())
                partial_text = partial.get("partial", "").lower().strip()
                
                if partial_text:
                    print(f"Partial: {partial_text}")
                    
                    # Check if any wake word variant is in the partial text
                    if any(word in partial_text for word in wake_words):
                        print("Wake word detected in partial result!")
                        # Consume the current buffer before returning
                        rec.Result()
                        return True
        except queue.Empty:
            pass

def listen_for_command(sound_listener, end_command=None):
    """Listen for a command until the end command is heard using Vosk"""
    if end_command is None:
        end_command = os.getenv("GO_PHRASE", "go for it").lower()
        
    print(f"Listening for your command. Say '{end_command}' when done.")
    
    full_command = ""
    start_time = time.time()
    timeout = int(os.getenv("COMMAND_TIMEOUT", "30"))  # timeout in seconds, configurable
    last_activity = time.time()
    silence_timeout = int(os.getenv("SILENCE_TIMEOUT", "5"))  # silence timeout in seconds, configurable
    
    # Start the listener if not already listening
    sound_listener.start_listening()
    
    try:
        while True:
            # Check for overall timeout
            if time.time() - start_time > timeout:
                print(f"Overall listening timeout reached ({timeout}s).")
                if not full_command:
                    return "Sorry, I didn't hear your command."
                break
                
            # Check for silence timeout
            if time.time() - last_activity > silence_timeout and full_command:
                print(f"Silence detected for {silence_timeout} seconds, finishing command.")
                break
            
            text = sound_listener.listen_for_phrase(timeout=1)
            if text:
                print(f"Heard: {text}")
                last_activity = time.time()
                
                if end_command in text.lower():
                    # Remove the end command from the final command
                    parts = text.lower().split(end_command, 1)
                    full_command += parts[0] + " "
                    break
                else:
                    full_command += text + " "
    finally:
        # Don't stop global listening here - we'll continue listening for wake word
        pass
    
    return full_command.strip()

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

def voice_mode():
    """Run the application in voice-activated mode"""
    # Get wake phrase from environment
    hi_phrase = os.getenv("HI_PHRASE", "listen up").lower()
    go_phrase = os.getenv("GO_PHRASE", "go for it").lower()
    pre_command = os.getenv("PRE_COMMAND", "hocus pocus").lower()
    post_command = os.getenv("POST_COMMAND", "abracadabra").lower()
    done_phrase = os.getenv("DONE_PHRASE", "that will do").lower()
    
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
                    if listen_for_wake_word(sound_listener):
                        in_conversation = True
                
                # If in a conversation or wake word detected, get command
                if in_conversation:
                    # Acknowledge the wake word or ready for next command
                    speak("yes", sound_listener)
                    
                    # Get command
                    command = listen_for_command(sound_listener)
                    
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
        cli_mode()

def main():
    # Get current settings for displaying in help
    current_hi_phrase = os.getenv("HI_PHRASE", "listen up")
    current_go_phrase = os.getenv("GO_PHRASE", "go for it")
    current_pre_command = os.getenv("PRE_COMMAND", "hocus pocus")
    current_post_command = os.getenv("POST_COMMAND", "abracadabra")
    current_done_phrase = os.getenv("DONE_PHRASE", "that will do")

    # Check for help flags before creating the parser
    if "-h" in sys.argv or "--help" in sys.argv:
        # Custom help message
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
        os.environ["VOSK_MODEL_PATH"] = args.model_path
    if args.hi:
        os.environ["HI_PHRASE"] = args.hi
    if args.go:
        os.environ["GO_PHRASE"] = args.go
    if args.done:
        os.environ["DONE_PHRASE"] = args.done
    
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
    if args.cli or not VOICE_MODE_AVAILABLE:
        if args.text:
            # CLI mode with initial query
            cli_mode_with_initial_text(" ".join(args.text))
        else:
            # Standard CLI mode
            cli_mode()
    else:
        try:
            voice_mode()
        except Exception as e:
            print(f"Error initializing voice mode: {e}")
            print("Falling back to CLI mode...")
            cli_mode()

if __name__ == "__main__":
    main()