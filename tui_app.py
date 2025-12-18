from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, LoadingIndicator, Label
from textual.worker import get_current_worker
from textual import work
import requests
import time
import json
import uuid  # Need this for unique IDs

# Import backend
import config
from database import get_db_connection, query_logs
from ingestor import start_ingestion_thread

# --- 1. THEME & STYLING (Purple/Cyberpunk) ---
CSS = """
Screen { background: #0d1117; color: #c9d1d9; }
#chat_container {
    height: 1fr; margin: 0 1; background: #0d1117;
    scrollbar-gutter: stable; overflow-y: scroll; border-top: solid #30363d;
}
Input {
    dock: bottom; margin: 0 1 1 1; border: tall #58a6ff;
    background: #161b22; color: #ffffff; height: 3;
}
Input:focus { border: tall #bd93f9; }
.user_msg {
    background: #4c2889; color: #ffffff; padding: 0 1; margin: 1 4 1 0;
    text-align: right; content-align: right middle;
    border-right: wide #bd93f9; width: 100%; height: auto;
}
.ai_msg {
    background: #21262d; color: #ff7b72; padding: 0 1; margin: 1 0 1 4;
    text-align: left; content-align: left middle;
    border-left: wide #ff7b72; width: 100%; height: auto;
}
.title_label {
    content-align: left middle; width: 100%; background: #161b22;
    color: #bd93f9; text-style: bold; height: 3; padding: 0 2;
    border-bottom: heavy #bd93f9;
}
LoadingIndicator { height: 1; color: #bd93f9; }
"""

# --- 2. HELPER: TIME FILTER ---
def get_time_filter(user_prompt):
    now = time.time()
    user_prompt = user_prompt.lower()
    if "last hour" in user_prompt: return {"timestamp": {"$gte": now - 3600}}
    if "today" in user_prompt or "24 hours" in user_prompt: return {"timestamp": {"$gte": now - 86400}}
    return None

# --- 3. THE APP CLASS ---
class LogChatApp(App):
    CSS = CSS
    BINDINGS = [("ctrl+q", "quit", "Quit App")]

    def compose(self) -> ComposeResult:
        yield Label(" 🐧 ARCH_LOG_ANALYST ", classes="title_label")
        with VerticalScroll(id="chat_container"):
            yield Markdown("> **System Ready.**")
            msg = Markdown("How can I assist?")
            msg.add_class("ai_msg")
            yield msg
        yield Input(placeholder="COMMAND >>", id="user_input")

    def on_mount(self) -> None:
        start_ingestion_thread()

    # --- 4. THE BRAIN (Now with Streaming) ---
    @work(exclusive=True, thread=True)
    def process_question(self, user_question: str):
        worker = get_current_worker()

        # A. Setup Context
        collection, model = get_db_connection()
        time_filter = get_time_filter(user_question)
        context = query_logs(user_question, collection, model, where_filter=time_filter)

        system_instruction = """
                You are a Log Analyst. 
                
                CRITICAL RULES:
                1. Base your answer ONLY on the provided logs.
                2. STRICTLY COPY the Timestamp from the log (e.g., "14:41:11"). 
                3. DO NOT try to convert timezones or calculate time difference.
                4. DO NOT invent events. If logs are empty, say "No activity found."
                5. Keep it short.
                """
        full_prompt = f"{system_instruction}\n\nLOG DATA:\n{context}\n\nUSER QUESTION: {user_question}\nANSWER:"

        # C. Generate UUID for the new message bubble
        # This ensures every message has a unique ID so we can update the correct one
        msg_id = f"ai_msg_{uuid.uuid4().hex}"
        
        # D. Create the Empty Bubble on Main Thread
        self.call_from_thread(self.create_streaming_bubble, msg_id)

        # E. Call Ollama with Streaming
        try:
            payload = {
                "model": config.OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": True # Enable Streaming
            }
            
            response = requests.post(config.OLLAMA_API, json=payload, stream=True)
            
            full_text = ""
            
            # F. Read the Stream
            for line in response.iter_lines():
                if worker.is_cancelled: break # Stop if user quits
                
                if line:
                    try:
                        json_data = json.loads(line)
                        chunk = json_data.get("response", "")
                        full_text += chunk
                        
                        # Update the specific message bubble
                        self.call_from_thread(self.update_streaming_bubble, msg_id, full_text)
                        
                        if json_data.get("done", False):
                            break
                    except:
                        continue
                        
        except Exception as e:
            self.call_from_thread(self.update_streaming_bubble, msg_id, f"❌ Error: {e}")

    # --- UI UPDATERS (Must be fast) ---
    
    def create_streaming_bubble(self, msg_id: str):
        """Creates an empty bubble ready to receive text."""
        # Remove spinner
        try: self.query_one(LoadingIndicator).remove()
        except: pass
        
        chat = self.query_one("#chat_container")
        
        # Create empty Markdown widget with unique ID
        msg = Markdown("...") 
        msg.add_class("ai_msg")
        msg.id = msg_id 
        
        chat.mount(msg)
        chat.scroll_end(animate=False)

    def update_streaming_bubble(self, msg_id: str, new_text: str):
        """Updates the text content of a specific bubble."""
        try:
            # Find the widget by its unique ID
            msg_widget = self.query_one(f"#{msg_id}", Markdown)
            msg_widget.update(new_text)
            
            # Optional: aggressive scrolling if you want it to auto-scroll
            # self.query_one("#chat_container").scroll_end(animate=False)
        except:
            pass

    # --- INPUT HANDLER ---
    def add_user_message(self, text: str):
        chat = self.query_one("#chat_container")
        msg = Markdown(f"{text}")
        msg.add_class("user_msg")
        chat.mount(msg)
        chat.scroll_end(animate=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        if not user_input: return

        self.query_one("#user_input").value = ""
        self.add_user_message(user_input)
        
        # Add spinner briefly (removed as soon as stream starts)
        self.query_one("#chat_container").mount(LoadingIndicator())
        self.query_one("#chat_container").scroll_end(animate=True)

        self.process_question(user_input)

if __name__ == "__main__":
    app = LogChatApp()
    app.run()