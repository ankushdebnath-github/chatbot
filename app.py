import os
import time
import json
import streamlit as st
import google.generativeai as genai
from rapidfuzz import process, fuzz
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Set page config as the FIRST Streamlit command
st.set_page_config(page_title="Business Proposal ChatBot", page_icon="📈", layout="wide")

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("⚠️ Missing API key. Please check your .env file.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-pro")

# Load business keywords from file
def load_business_keywords(file_path="business_keywords.txt"):
    try:
        with open(file_path, "r") as file:
            keywords = [line.strip() for line in file if line.strip()]
        return keywords
    except FileNotFoundError:
        return ["business", "investment", "startup", "revenue", "profit", "marketing"]
    except Exception as e:
        print(f"Error loading keywords: {str(e)}")
        return []

BUSINESS_TOPICS = load_business_keywords()
NON_BUSINESS_PHRASES = ["hi", "hello", "how are you", "hey", "good morning"]
NON_BUSINESS_TOPICS = ["football", "sports", "game", "play", "weather", "food", "eat", "drink"]

# Functions for conversation persistence
CONVERSATIONS_FILE = "conversations.json"

def load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_conversation(conversation_id, chat_history):
    conversations = load_conversations()
    conversations[conversation_id] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "history": chat_history
    }
    with open(CONVERSATIONS_FILE, "w") as f:
        json.dump(conversations, f, indent=2)

def delete_conversation(conversation_id):
    conversations = load_conversations()
    if conversation_id in conversations:
        del conversations[conversation_id]
        with open(CONVERSATIONS_FILE, "w") as f:
            json.dump(conversations, f, indent=2)

def correct_spelling(query):
    if not query:
        return ""
    best_match = process.extractOne(query.lower(), BUSINESS_TOPICS, scorer=fuzz.partial_ratio)
    if isinstance(best_match, tuple) and len(best_match) >= 2:
        match_text, score = best_match[:2]
        return match_text if score >= 75 else query
    return query

def is_business_related(query):
    query_lower = query.lower().strip()
    if query_lower in NON_BUSINESS_PHRASES or any(topic in query_lower for topic in NON_BUSINESS_TOPICS):
        return False
    best_match = process.extractOne(query, BUSINESS_TOPICS, scorer=fuzz.partial_ratio)
    if isinstance(best_match, tuple) and len(best_match) >= 2:
        return best_match[1] > 80
    return False

def is_part_of_business_conversation(query, prev_business_flag):
    query_lower = query.lower().strip()
    if query_lower in NON_BUSINESS_PHRASES or any(topic in query_lower for topic in NON_BUSINESS_TOPICS):
        return False
    best_match = process.extractOne(query, BUSINESS_TOPICS, scorer=fuzz.partial_ratio)
    if isinstance(best_match, tuple) and len(best_match) >= 2:
        return best_match[1] > 50 if prev_business_flag else best_match[1] > 80
    return False

# Load Tailwind CSS and custom styles
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        /* Custom fonts */
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Global styling */
        body, .stApp {
            font-family: 'Inter', sans-serif;
            background-color: #1a1a1a;
            color: #d1d5db;
        }

        /* Main container */
        .main-container {
            display: flex;
            min-height: 100vh;
        }

        /* Sidebar styling */
        .css-1d391kg {
            background: linear-gradient(180deg, #121212, #1a1a1a);
            width: 300px !important;
            padding: 20px;
            border-right: 1px solid #2a2a2a;
            height: 100vh;
            overflow-y: auto;
            transition: transform 0.3s ease-in-out;
        }

        /* Sidebar hidden state */
        .sidebar-hidden {
            transform: translateX(-100%);
        }

        /* Sidebar visible state */
        .sidebar-visible {
            transform: translateX(0);
        }

        /* Sidebar header */
        .sidebar-header {
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Sidebar section labels (Today, Previous 7 Days) */
        .section-label {
            font-size: 14px;
            font-weight: 600;
            color: #8e8ea0;
            margin: 16px 0 8px;
            position: relative;
        }
        .section-label::after {
            content: '';
            position: absolute;
            bottom: -4px;
            left: 0;
            width: 100%;
            height: 1px;
            background-color: #2a2a2a;
        }

        /* Conversation item */
        .conversation-item {
            background-color: #2a2a2a;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: background-color 0.2s ease, transform 0.1s ease;
            position: relative;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }
        .conversation-item:hover {
            background-color: #3a3a3a;
            transform: translateX(2px);
        }
        .conversation-item.selected {
            background-color: #1f3a44;
            border-left: 4px solid #10b981;
            padding-left: 8px;
        }

        /* Conversation text */
        .conversation-text {
            flex: 1;
            overflow: hidden;
        }
        .conversation-id {
            font-size: 14px;
            font-weight: 500;
            color: #d1d5db;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 180px;
        }
        .conversation-timestamp {
            font-size: 12px;
            color: #8e8ea0;
            margin-top: 2px;
        }

        /* Delete button (Streamlit button styling) */
        div[data-testid="stButton"] button[kind="secondary"][id^="delete_"] {
            background-color: #ef4444;
            color: white;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            border: none;
            transition: background-color 0.2s ease;
        }
        div[data-testid="stButton"] button[kind="secondary"][id^="delete_"]:hover {
            background-color: #dc2626;
        }

        /* New conversation button (Streamlit button styling) */
        div[data-testid="stButton"] button[kind="secondary"][id="new_conv"] {
            background: linear-gradient(90deg, #10b981, #059669);
            color: white;
            border-radius: 6px;
            padding: 10px 16px;
            font-weight: 600;
            border: none;
            width: 100%;
            text-align: center;
            margin-top: 16px;
            transition: background-color 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        div[data-testid="stButton"] button[kind="secondary"][id="new_conv"]:hover {
            background: linear-gradient(90deg, #059669, #10b981);
        }

        /* Chat container */
        .chat-container {
            flex: 1;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            max-width: 800px;
            margin: 0 auto;
        }

        /* Chat history */
        .chat-history {
            flex: 1;
            overflow-y: auto;
            padding-bottom: 20px;
        }

        /* Assistant message (robotic theme) */
        .assistant-message {
            font-family: 'Roboto Mono', monospace;
            background-color: #2a2a2a;
            color: #d1d5db;
            border-left: 4px solid #10b981;
            padding: 12px 18px;
            border-radius: 8px;
            margin: 10px 0;
            max-width: 80%;
        }

        /* User message */
        .user-message {
            background-color: #3b82f6;
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 8px;
            margin: 10px 0;
            max-width: 80%;
        }

        /* Input box */
        .stTextInput input {
            background-color: #2a2a2a;
            color: #d1d5db;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            padding: 12px;
        }
        .stTextInput input::placeholder {
            color: #8e8ea0;
        }

        /* Toggle button (Streamlit button styling) */
        div[data-testid="stButton"] button[kind="secondary"][id="toggle_sidebar"] {
            background-color: #2a2a2a;
            color: #d1d5db;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            padding: 8px 12px;
            transition: background-color 0.3s ease;
        }
        div[data-testid="stButton"] button[kind="secondary"][id="toggle_sidebar"]:hover {
            background-color: #3a3a3a;
        }

        /* App Builder section */
        .app-builder-section {
            background-color: #2a2a2a;
            padding: 16px;
            border-radius: 8px;
            position: relative;
            margin-bottom: 20px;
        }
        .app-builder-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Close button for App Builder (Streamlit button styling) */
        div[data-testid="stButton"] button[kind="secondary"][id="close_app_builder"] {
            position: absolute;
            top: 8px;
            right: 8px;
            background-color: #ef4444;
            color: white;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: none;
            font-size: 14px;
            transition: background-color 0.2s ease;
            padding: 0;
        }
        div[data-testid="stButton"] button[kind="secondary"][id="close_app_builder"]:hover {
            background-color: #dc2626;
        }

        /* Footer */
        .footer {
            text-align: center;
            color: #8e8ea0;
            font-size: 12px;
            margin-top: 20px;
        }
        .footer a {
            color: #3b82f6;
            text-decoration: underline;
        }

        /* Hide Streamlit's default sidebar toggle */
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* Hide Streamlit buttons for Select (only show the ones we style explicitly) */
        div[data-testid="stButton"] button[id^="select_"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# Toggleable sidebar
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = False

# Sidebar toggle button
st.markdown('<div class="fixed top-4 left-4">', unsafe_allow_html=True)
if st.button("☰ Conversations", key="toggle_sidebar"):
    print("Toggle Sidebar button clicked")
    st.session_state.sidebar_open = not st.session_state.sidebar_open
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar with conversation list
if st.session_state.sidebar_open:
    sidebar_class = "sidebar-visible"
else:
    sidebar_class = "sidebar-hidden"

with st.sidebar:
    st.markdown(f'<div class="{sidebar_class}">', unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-header">🗨️ Conversations</div>', unsafe_allow_html=True)
    
    # Group conversations by "Today" and "Previous 7 Days"
    conversations = load_conversations()
    today = datetime.now()
    one_week_ago = today - timedelta(days=7)
    
    today_convs = {}
    last_week_convs = {}
    
    for conv_id, data in conversations.items():
        conv_time = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
        if conv_time >= today.replace(hour=0, minute=0, second=0, microsecond=0):
            today_convs[conv_id] = data
        elif conv_time >= one_week_ago:
            last_week_convs[conv_id] = data
    
    # Today section
    if today_convs:
        st.markdown('<div class="section-label">Today</div>', unsafe_allow_html=True)
        for conv_id, data in today_convs.items():
            is_selected = st.session_state.get("selected_conversation", "") == f"{conv_id} ({data['timestamp']})"
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                    <div class="conversation-item {'selected' if is_selected else ''}" 
                         onclick="document.getElementById('select_{conv_id}').click()"
                         title="{conv_id} ({data['timestamp']})">
                        <div class="conversation-text">
                            <div class="conversation-id">{conv_id}</div>
                            <div class="conversation-timestamp">{data['timestamp']}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Select", key=f"select_{conv_id}", help="Select this conversation"):
                    print(f"Select button clicked for conversation: {conv_id}")
                    st.session_state.selected_conversation = f"{conv_id} ({data['timestamp']})"
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{conv_id}", help="Delete this conversation"):
                    print(f"Delete button clicked for conversation: {conv_id}")
                    delete_conversation(conv_id)
                    if st.session_state.get("selected_conversation") == f"{conv_id} ({data['timestamp']})":
                        st.session_state.selected_conversation = "New Conversation"
                    st.rerun()
    
    # Previous 7 Days section
    if last_week_convs:
        st.markdown('<div class="section-label">Previous 7 Days</div>', unsafe_allow_html=True)
        for conv_id, data in last_week_convs.items():
            is_selected = st.session_state.get("selected_conversation", "") == f"{conv_id} ({data['timestamp']})"
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                    <div class="conversation-item {'selected' if is_selected else ''}" 
                         onclick="document.getElementById('select_{conv_id}').click()"
                         title="{conv_id} ({data['timestamp']})">
                        <div class="conversation-text">
                            <div class="conversation-id">{conv_id}</div>
                            <div class="conversation-timestamp">{data['timestamp']}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Select", key=f"select_{conv_id}", help="Select this conversation"):
                    print(f"Select button clicked for conversation: {conv_id}")
                    st.session_state.selected_conversation = f"{conv_id} ({data['timestamp']})"
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{conv_id}", help="Delete this conversation"):
                    print(f"Delete button clicked for conversation: {conv_id}")
                    delete_conversation(conv_id)
                    if st.session_state.get("selected_conversation") == f"{conv_id} ({data['timestamp']})":
                        st.session_state.selected_conversation = "New Conversation"
                    st.rerun()
    
    # New Conversation button
    if st.button("➕ New Conversation", key="new_conv", help="Start a new conversation"):
        print("New Conversation button clicked")
        st.session_state.selected_conversation = "New Conversation"
        st.session_state.chat_history = []
        st.session_state.welcome_shown = False
        st.session_state.conversation_id = f"conv_{int(time.time())}"
        st.session_state.is_conversation_business_related = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Main chat area
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Title
st.markdown('<h1 class="text-3xl font-bold text-gray-200 text-center mb-6">Business Proposal ChatBot</h1>', unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_conversation_business_related" not in st.session_state:
    st.session_state.is_conversation_business_related = False
if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{int(time.time())}"
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False
if "selected_conversation" not in st.session_state:
    st.session_state.selected_conversation = "New Conversation"
if "show_app_builder" not in st.session_state:
    st.session_state.show_app_builder = True

# Load selected conversation and manage welcome message
if st.session_state.selected_conversation != "New Conversation":
    conv_id = st.session_state.selected_conversation.split(" (")[0]
    conversations = load_conversations()
    if conv_id in conversations:
        st.session_state.chat_history = conversations[conv_id]["history"]
        st.session_state.conversation_id = conv_id
        st.session_state.is_conversation_business_related = any(
            is_business_related(msg[1]) for msg in st.session_state.chat_history if msg[0] == "user"
        )
        st.session_state.welcome_shown = True
else:
    if not st.session_state.chat_history and not st.session_state.welcome_shown:
        welcome_message = "Welcome to the Business Proposal ChatBot! How can I assist you with your business queries today?"
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f'<div class="assistant-message">{welcome_message}</div>', unsafe_allow_html=True)
        st.session_state.chat_history.append(("assistant", welcome_message))
        st.session_state.welcome_shown = True

# Chat history
st.markdown('<div class="chat-history">', unsafe_allow_html=True)
for role, message in st.session_state.chat_history:
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="user-message">{message}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f'<div class="assistant-message">{message}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Input area with buttons
st.markdown("""
    <div class="bg-[#2a2a2a] p-4 rounded-lg mb-4">
        <div class="flex items-center space-x-2 mb-2">
            <span class="text-gray-400">Message Business Proposal ChatBot</span>
            <div class="flex space-x-2">
                <button class="text-gray-400 hover:text-gray-200">🌐 Web Search</button>
                <button class="text-gray-400 hover:text-gray-200">📱 App Builder</button>
                <button class="text-gray-400 hover:text-gray-200">🔍 Deep Research</button>
                <button class="text-gray-400 hover:text-gray-200">💡 Think</button>
                <button class="text-gray-400 hover:text-gray-200">📤 Upload</button>
                <button class="text-gray-400 hover:text-gray-200">🎨 Figma</button>
            </div>
        </div>
""", unsafe_allow_html=True)

user_prompt = st.chat_input("Ask a business-related question...")

st.markdown('</div>', unsafe_allow_html=True)

# Additional section (App Builder) with close button
if st.session_state.show_app_builder:
    st.markdown("""
        <div class="app-builder-section">
            <div class="app-builder-content">
                <div>
                    <h3 class="text-lg font-semibold text-gray-200">New: App Builder</h3>
                    <p class="text-gray-400">Build complete apps in seconds, backend, frontend, database, no limits.</p>
                </div>
                <button class="bg-gray-700 text-white py-2 px-4 rounded-lg hover:bg-gray-600 transition">
                    Try Now
                </button>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("✕", key="close_app_builder", help="Close the App Builder section"):
        print("Close App Builder button clicked")
        st.session_state.show_app_builder = False
        st.rerun()

# Handle user input
COOLDOWN = 2
if user_prompt:
    if time.time() - st.session_state.last_request_time < COOLDOWN:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown('<div class="assistant-message">⏳ Please wait a moment before sending another request.</div>', unsafe_allow_html=True)
    else:
        st.session_state.last_request_time = time.time()
        corrected_prompt = correct_spelling(user_prompt)

        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="user-message">{user_prompt}</div>', unsafe_allow_html=True)
        
        with st.spinner("Thinking..."):
            is_business = is_part_of_business_conversation(corrected_prompt, st.session_state.is_conversation_business_related)
            if is_business:
                try:
                    gemini_response = gemini_model.generate_content(corrected_prompt).text
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(f'<div class="assistant-message">{gemini_response}</div>', unsafe_allow_html=True)
                    st.session_state.chat_history.append(("user", user_prompt))
                    st.session_state.chat_history.append(("assistant", gemini_response))
                    st.session_state.is_conversation_business_related = True
                except Exception as e:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(f'<div class="assistant-message">⚠️ Error: {str(e)}</div>', unsafe_allow_html=True)
                    st.session_state.chat_history.append(("user", user_prompt))
                    st.session_state.chat_history.append(("assistant", f"⚠️ Error: {str(e)}"))
            else:
                response = "I’m here to help with business-related queries only. Ask me about startups, marketing, or investments!"
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(f'<div class="assistant-message">{response}</div>', unsafe_allow_html=True)
                st.session_state.chat_history.append(("user", user_prompt))
                st.session_state.chat_history.append(("assistant", response))
                if user_prompt.lower().strip() in NON_BUSINESS_PHRASES or any(topic in user_prompt.lower() for topic in NON_BUSINESS_TOPICS):
                    st.session_state.is_conversation_business_related = False
        
        # Save the conversation with the current conversation_id
        save_conversation(st.session_state.conversation_id, st.session_state.chat_history)

# Footer
st.markdown("""
    <div class="footer">
        <a href="https://x.com">Follow us on X</a> • 
        By using Business Proposal ChatBot you agree to the <a href="#">Terms</a> & <a href="#">Privacy</a>
    </div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
