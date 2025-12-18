# config.py
import os

# Paths
# LOG_FILE_PATH = "/var/log/pacman.log"
LOG_FILE_PATH = "/var/log/system.log"
DB_PATH = "./my_log_db"
COLLECTION_NAME = "system_logs"

# AI Settings
OLLAMA_MODEL = "phi3"
OLLAMA_API = "http://localhost:11434/api/generate"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ensure log file exists to prevent errors
if not os.path.exists(LOG_FILE_PATH):
    try:
        open(LOG_FILE_PATH, 'w').close()
    except PermissionError:
        pass # Handle in main app