#!/usr/bin/env python
import json
import queue
import time
import numpy as np

# Try to import optional voice recognition modules
try:
    import vosk
    import sounddevice as sd
    VOICE_AVAILABLE = True
except ImportError as e:
    VOICE_AVAILABLE = False
    print(f"Warning: Voice recognition modules couldn't be imported: {e}")
    print("Voice mode will not be available. Using CLI mode only.")

class SoundDeviceListener:
    """Class for managing Vosk-based speech recognition with sounddevice"""
    def __init__(self, model_path):
        if not VOICE_AVAILABLE:
            raise ImportError("Voice recognition modules (vosk and sounddevice) are required")
            
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

def listen_for_wake_word(sound_listener, wake_phrase):
    """Listen continuously for the wake word using Vosk with improved detection"""
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

def listen_for_command(sound_listener, end_command, timeout, silence_timeout):
    """Listen for a command until the end command is heard using Vosk"""
    print(f"Listening for your command. Say '{end_command}' when done.")
    
    full_command = ""
    start_time = time.time()
    last_activity = time.time()
    
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