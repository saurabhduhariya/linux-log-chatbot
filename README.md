# Linux Log Chatbot 🐧

A smart log analysis tool that lets you chat with your Linux logs using a local LLM (Ollama). It supports both a Web UI (Streamlit) and a Terminal UI (Textual).

## Features
- **Natural Language Queries:** Ask questions like "Show me errors from the last hour".
- **Dual Interface:** Choose between a web dashboard or a terminal interface.
- **Local AI:** Uses Ollama (Phi-3) for privacy and offline capability.
- **Real-time Ingestion:** Automatically watches and indexes new log entries.

## Prerequisites
- Python 3.8+
- [Ollama](https://ollama.com/) installed and running (`ollama run phi3`).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/saurabhduhariya/linux-log-chatbot.git
   cd linux-log-chatbot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: If `requirements.txt` is missing, install: `streamlit textual chromadb requests sentence-transformers`)*

3. Configure the log path in `config.py`:
   ```python
   LOG_FILE_PATH = "server_app.log"  # or /var/log/syslog
   ```

## Usage

### 1. Generate Dummy Logs (Optional)
If you don't have a log file ready, generate one:
```bash
python generate_logs.py
```

### 2. Run the Web Interface
```bash
streamlit run app.py
```

### 3. Run the Terminal Interface (TUI)
```bash
python tui_app.py
```

## Configuration
Edit `config.py` to change:
- `LOG_FILE_PATH`: Path to the log file you want to monitor.
- `OLLAMA_MODEL`: The LLM model to use (default: `phi3`).
