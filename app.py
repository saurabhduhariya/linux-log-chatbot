import streamlit as st
import requests
import time
import config
from database import get_db_connection, query_logs
from ingestor import start_ingestion_thread

# --- PAGE SETUP ---
st.set_page_config(page_title="Arch Log Analyst", page_icon="🐧")
st.title("🐧 Arch Linux Log Analyst")
st.caption(f"Monitoring: `{config.LOG_FILE_PATH}`")

# --- START BACKGROUND WORKER ---
# This runs ingestor.py in the background automatically
if "ingestion_started" not in st.session_state:
    start_ingestion_thread()
    st.session_state.ingestion_started = True
    st.success("Background Ingestion Service Started.")

# --- HELPER: DETECT TIME INTENT ---
def get_time_filter(user_prompt):
    """
    Translates English time phrases into Unix timestamp filters.
    Returns a ChromaDB 'where' filter dictionary or None.
    """
    now = time.time()
    user_prompt = user_prompt.lower()
    
    # 1 Hour = 3600 seconds
    if "last hour" in user_prompt or "last 1 hour" in user_prompt:
        return {"timestamp": {"$gte": now - 3600}}
    
    # 1 Day = 86400 seconds
    if "today" in user_prompt or "last 24 hours" in user_prompt or "last day" in user_prompt:
        return {"timestamp": {"$gte": now - 86400}}
        
    # Last week = 604800 seconds
    if "last week" in user_prompt:
        return {"timestamp": {"$gte": now - 604800}}
        
    return None # No filter, search everything

# --- CHAT UI ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- MAIN CHAT LOGIC ---
if prompt := st.chat_input("Ask about your logs..."):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Retrieve Context (With Filtering)
    collection, model = get_db_connection()
    
    # Calculate Filter based on user input
    time_filter = get_time_filter(prompt)
    
    # --- DEBUG BLOCK (Add this temporarily) ---
    # if time_filter:
    #     import datetime
    #     st.caption("🕒 Focusing on recent logs...")
        
    #     # 1. What time is it now?
    #     now_ts = time.time()
    #     now_readable = datetime.datetime.fromtimestamp(now_ts).strftime('%Y-%m-%d %H:%M:%S')
        
        # # 2. What is the filter cutoff?
        # # We know the structure is {'timestamp': {'$gte': SOME_VALUE}}
        # cutoff_ts = time_filter['timestamp']['$gte']
        # cutoff_readable = datetime.datetime.fromtimestamp(cutoff_ts).strftime('%Y-%m-%d %H:%M:%S')
        
        # # 3. Show the comparison
        # st.info(f"""
        # **Debug Info:**
        # * System "Now": `{now_readable}` (TS: {now_ts:.0f})
        # * Filter Cutoff: `{cutoff_readable}` (TS: {cutoff_ts:.0f})
        # * Searching for logs NEWER than the Cutoff.
        # """)
    # ------------------------------------------

    if time_filter:
        st.caption("🕒 Focusing on recent logs...")
    # Pass the filter to the database query
    context = query_logs(prompt, collection, model, where_filter=time_filter)

    # 3. Generate Answer
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                system_instruction = """
                You are a helpful Linux Assistant.
                Summarize the logs in plain English for a non-technical user.
                
                RULES:
                1. Keep answers SHORT (max 2-3 sentences).
                2. Avoid technical jargon or long version numbers.
                3. Group similar actions (e.g., instead of listing 10 files, say "System libraries were updated").
                4. STRICTLY use the provided logs.
                5. If logs are empty, say: "No logs found for this time."
                """
                
                full_prompt = f"{system_instruction}\n\nLOG DATA:\n{context}\n\nUSER QUESTION: {prompt}\nANSWER:"
                payload = {
                    "model": config.OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False
                }
                
                response = requests.post(config.OLLAMA_API, json=payload)
                answer = response.json()['response']
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except Exception as e:
                st.error(f"Error connecting to Ollama: {e}")