## Future Improvements

Future versions could include:
- Voice input using speech recognition
- Support for Windows and Linux text-to-speech
- Better handling of long responses
- Interface improvements
- Custom system prompts# Secret Friend

A simple command-line interface to interact with local LLMs through Ollama, with text-to-speech feedback.

## Overview

Secret Friend is a Python script that allows you to have a voice conversation with LLMs running on your local machine via [Ollama](https://ollama.ai/). You type your questions or prompts, and the LLM's responses are spoken aloud using macOS's built-in text-to-speech capability.

## Requirements

- macOS (for the built-in `say` command)
- Python 3.x
- [Ollama](https://ollama.ai/) installed and running locally with at least one model
- `requests` Python package

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/smurp/secretfriend.git
   cd secretfriend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Make sure Ollama is installed and running:
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # If not running, start Ollama in a separate terminal
   ollama serve
   
   # You should be able to visit http://localhost:11434 in your browser
   # and see "Ollama is running" if the service is active
   ```

5. Pull at least one model if you haven't already:
   ```bash
   ollama pull gemma2:latest
   # or any other model you prefer
   ```

6. Make the script executable:
   ```bash
   chmod +x secretfriend.py
   ```

## Usage

1. Run the script:
   ```bash
   ./secretfriend.py
   ```

2. Type your question or prompt and press Enter.

3. The script will send your prompt to the local LLM and speak the response.

4. Type 'exit' to quit the program.

## Features

- Uses locally running LLMs via Ollama
- Text-to-speech output using macOS's built-in `say` command
- Automatically detects available models
- Cleans LLM responses for better speech output
- Simple command-line interface

## Configuration

You can configure Secret Friend using environment variables or a `.env` file:

- `MODEL`: Specify which Ollama model to use (default: gemma2:latest)

Examples:

```bash
# Run with a specific model
MODEL=deepseek-r1:32b ./secretfriend.py

# Or create a .env file with the configuration
echo "MODEL=deepseek-r1:32b" > .env
./secretfriend.py
```

## Troubleshooting

### Ollama Connection Issues

If you get an error like "Error communicating with Ollama API", check that:

1. Ollama is installed and running
   ```bash
   # Check if the Ollama process is running
   ps aux | grep ollama
   
   # Check if the API is responding
   curl http://localhost:11434/api/tags
   ```

2. If Ollama isn't running, start it in a separate terminal:
   ```bash
   ollama serve
   ```

3. Verify you have at least one model installed:
   ```bash
   ollama list
   ```

4. If no models are installed, pull one:
   ```bash
   ollama pull gemma2:latest
   # or
   ollama pull llama3
   ```

### Text-to-Speech Issues

If the responses appear but aren't being spoken:

1. Test if the macOS 'say' command works independently:
   ```bash
   say "This is a test"
   ```

2. Check for any error messages in the script output when it attempts to speak

3. Try running the script with a different terminal or shell if the speech isn't working

## License

MIT License

## Acknowledgments

- [Ollama](https://ollama.ai/) for making local LLMs easy to use