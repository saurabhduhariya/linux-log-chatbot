import time
import os
import hashlib
import threading
import re # <--- NEW
from datetime import datetime # <--- NEW
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import config
from database import get_db_connection

def extract_timestamp(line):
    # Regex to find: 2025-12-17T16:16:00+05:30
    match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
    
    if match:
        try:
            # We ignore the +05:30 part for parsing to keep it simple and avoid errors
            # This treats the time as "Local Time" immediately
            dt_str = match.group(1) 
            dt = datetime.fromisoformat(dt_str)
            return dt.timestamp()
        except:
            pass
            
    return time.time()

def run_background_process():
    print("--- [Background] Starting Service with Time Awareness ---")
    collection, model = get_db_connection()

    # --- 1. SMART GAP FILL ---
    try:
        if not os.path.exists(config.LOG_FILE_PATH):
            open(config.LOG_FILE_PATH, 'w').close()
            
        with open(config.LOG_FILE_PATH, 'r', errors='ignore') as f:
            lines = f.readlines()[-1000:]
            
        ids, docs, embeddings, metadatas = [], [], [], []
        seen_ids = set() # <--- NEW: Keeps track of IDs in this batch
        
        for line in lines:
            if not line.strip(): continue
            
            line_hash = hashlib.md5(line.encode('utf-8')).hexdigest()
            
            # <--- NEW: If we already have this ID in the current batch, skip it!
            if line_hash in seen_ids:
                continue
            
            seen_ids.add(line_hash)
            
            # Process as normal
            ts = extract_timestamp(line)
            ids.append(line_hash)
            docs.append(line)
            embeddings.append(model.encode(line).tolist())
            metadatas.append({"timestamp": ts})
            
        if docs:
            collection.upsert(
                embeddings=embeddings, 
                documents=docs, 
                ids=ids,
                metadatas=metadatas
            )
            print(f"--- [Background] Gap fill complete. Processed {len(docs)} unique lines. ---")
            
    except Exception as e:
        print(f"Error during gap fill: {e}")

    # --- 2. REAL-TIME WATCHDOG ---
    class LogHandler(FileSystemEventHandler):
        def __init__(self, filename):
            self.filename = filename
            try:
                self.file = open(filename, 'r')
                self.file.seek(0, 2)
            except:
                open(filename, 'w').close()
                self.file = open(filename, 'r')

        def on_modified(self, event):
            if event.src_path.endswith(self.filename):
                lines = self.file.readlines()
                for line in lines:
                    if line.strip():
                        line_hash = hashlib.md5(line.encode('utf-8')).hexdigest()
                        vector = model.encode(line).tolist()
                        ts = extract_timestamp(line) # <--- Extract time
                        
                        collection.upsert(
                            embeddings=[vector], 
                            documents=[line], 
                            ids=[line_hash],
                            metadatas=[{"timestamp": ts}] # <--- Save it!
                        )
                        print(f"[New Log] {line[:20]}...")

    # ... (Rest of the file is the same as before) ...
    event_handler = LogHandler(config.LOG_FILE_PATH)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(config.LOG_FILE_PATH) or '.', recursive=False)
    observer.start()

    try:
        while True: time.sleep(1)
    except:
        observer.stop()

# ... (start_ingestion_thread function remains the same) ...
def start_ingestion_thread():
    t = threading.Thread(target=run_background_process, daemon=True)
    t.start()
    return t