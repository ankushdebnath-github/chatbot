import os
import time
import json
import streamlit as st
import requests
from rapidfuzz import process, fuzz
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Set page config (must be first Streamlit command)
st.set_page_config(page_title="Business Proposal ChatBot", page_icon="💼", layout="wide")

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    st.error("⚠️ Missing OpenRouter API key. Please check your .env file.")
    st.stop()

# Configuration
SITE_URL = "http://localhost:8501"  # Adjust based on your deployment
SITE_NAME = "Business AI Assistant"

# Business keywords
def load_business_keywords(file_path="business_keywords.txt"):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return ["business", "proposal", "investment", "startup", "revenue", "profit", "marketing"]
    except Exception as e:
        print(f"Error loading keywords: {e}")
        return []

BUSINESS_TOPICS = load_business_keywords()
NON_BUSINESS_PHRASES = [""]
NON_BUSINESS_TOPICS = ["football", "sports", "game", "weather", "food"]

# Conversation persistence
CONVERSATIONS_FILE = "conversations.json"

def load_conversations():
    return json.load(open(CONVERSATIONS_FILE, "r")) if os.path.exists(CONVERSATIONS_FILE) else {}

def save_conversation(conv_id, history):
    conversations = load_conversations()
    conversations[conv_id] = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "history": history}
    with open(CONVERSATIONS_FILE, "w") as f:
        json.dump(conversations, f, indent=2)

def delete_conversation(conv_id):
    conversations = load_conversations()
    if conv_id in conversations:
        del conversations[conv_id]
        with open(CONVERSATIONS_FILE, "w") as f:
            json.dump(conversations, f, indent=2)

# Business topic detection
def is_business_related(query):
    query_lower = query.lower().strip()
    if query_lower in NON_BUSINESS_PHRASES or any(topic in query_lower for topic in NON_BUSINESS_TOPICS):
        return False
    best_match = process.extractOne(query_lower, BUSINESS_TOPICS, scorer=fuzz.partial_ratio)
    return best_match[1] > 80 if isinstance(best_match, tuple) and len(best_match) >= 2 else False

# OpenRouter API call
def call_openrouter_api(messages):
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': SITE_URL,
                'X-Title': SITE_NAME
            },
            json={
                'model': 'deepseek/deepseek-chat-v3-0324:free',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 1000
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API Call Error: {e}")
        raise e

def generate_response(prompt, history):
    system_prompt = {
        "role": "system",
        "content": """You are a professional business assistant AI. Your responses should:
1. Use rich Markdown formatting (headers, lists, bold, italics)
2. Structure information clearly with sections
3. Include emojis for visual appeal
4. For business questions, provide detailed, formatted advice
5. For non-business questions, politely respond with:
   "I specialize in business topics. Please ask about marketing, finance, strategy, or related subjects."

Format business advice like this example:

🕯️ **Candle Business Success Guide**
*How to Differentiate & Scale*

### ✨ Product Development
- **Unique Scents**: Experiment with seasonal blends
- **Premium Materials**: Use soy wax + cotton wicks
- **Packaging**: Eco-friendly boxes with custom labels

### 📈 Marketing Strategy
1. Instagram: Post lifestyle photos 3x/week
2. Collaborations: Partner with local boutiques
3. Email: Collect addresses for promotions

Would you like me to focus on any specific area?"""
    }
    # Convert history to OpenRouter format (role: user/assistant)
    messages = [system_prompt] + [
        {"role": role, "content": content}
        for role, content in history
    ] + [{"role": "user", "content": prompt}]
    
    try:
        response = call_openrouter_api(messages)
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# Enhanced dark theme with sidebar calculator styling
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body, .stApp { 
            font-family: 'Inter', sans-serif; 
            background: #0a0a0a; 
            color: #d4d4d4; 
        }
        .main-container { 
            display: flex; 
            min-height: 100vh; 
            background: linear-gradient(135deg, #0a0a0a 0%, #141414 100%); 
            position: relative; 
            overflow: hidden; 
        }
        .main-container::before { 
            content: ''; 
            position: absolute; 
            top: -50%; 
            left: -50%; 
            width: 200%; 
            height: 200%; 
            background: radial-gradient(circle, rgba(80, 255, 150, 0.05) 0%, rgba(0, 0, 0, 0) 70%); 
            animation: pulseGlow 10s infinite; 
        }
        .chat-container { 
            flex: 1; 
            max-width: 950px; 
            margin: 20px auto; 
            padding: 30px; 
            background: #1a1a1a; 
            border-radius: 20px; 
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(80, 255, 150, 0.15); 
            position: relative; 
            z-index: 1; 
        }
        .chat-header { 
            text-align: center; 
            margin-bottom: 20px; 
            animation: fadeInDown 1s ease; 
        }
        .chat-history { 
            max-height: 650px; 
            overflow-y: auto; 
            padding: 20px; 
            background: #1a1a1a; 
            border-radius: 12px; 
            border: 1px solid rgba(80, 255, 150, 0.2); 
        }
        .assistant-message { 
            background: linear-gradient(135deg, #2a2a2a, #333333); 
            border: 1px solid #50ff96; 
            border-radius: 12px; 
            padding: 15px 20px; 
            margin: 10px 0; 
            max-width: 85%; 
            box-shadow: 0 3px 10px rgba(80, 255, 150, 0.25); 
            animation: slideInLeft 0.5s ease; 
        }
        .user-message { 
            background: linear-gradient(135deg, #6b7280, #4b5563); 
            color: #ffffff; 
            border: 1px solid #50ff96; 
            border-radius: 12px; 
            padding: 15px 20px; 
            margin: 10px 0; 
            max-width: 85%; 
            margin-left: auto; 
            box-shadow: 0 3px 10px rgba(80, 255, 150, 0.25); 
            animation: slideInRight 0.5s ease; 
        }
        .sidebar-visible { 
            width: 300px; 
            background: #121212; 
            color: #d4d4d4; 
            padding: 25px; 
            border-right: 1px solid #1f1f1f; 
            height: 100vh; 
            position: fixed; 
            transition: transform 0.4s ease-in-out; 
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.8); 
            z-index: 2; 
        }
        .sidebar-hidden { 
            transform: translateX(-100%); 
        }
        .conversation-item { 
            background: #1f1f1f; 
            padding: 12px; 
            border-radius: 10px; 
            margin: 6px 0; 
            cursor: pointer; 
            transition: all 0.3s ease; 
            border: 1px solid #333333; 
        }
        .conversation-item:hover { 
            background: #2a2a2a; 
            border-color: #50ff96; 
            transform: scale(1.02); 
        }
        .conversation-item.selected { 
            background: #2a2a2a; 
            border-left: 4px solid #50ff96; 
            box-shadow: 0 0 12px rgba(80, 255, 150, 0.4); 
        }
        .input-container { 
            background: #1a1a1a; 
            padding: 12px; 
            border-radius: 12px; 
            border: 1px solid #50ff96; 
            box-shadow: 0 0 10px rgba(80, 255, 150, 0.3), inset 0 0 8px rgba(80, 255, 150, 0.1); 
            animation: pulseBorder 2s infinite; 
        }
        .stTextInput input { 
            background: #121212; 
            border: 1px solid #50ff96; 
            border-radius: 10px; 
            padding: 12px; 
            color: #d4d4d4; 
            box-shadow: inset 0 0 5px rgba(80, 255, 150, 0.2); 
            transition: box-shadow 0.3s ease; 
        }
        .stTextInput input:focus { 
            box-shadow: 0 0 15px rgba(80, 255, 150, 0.5); 
        }
        .stTextInput input::placeholder { 
            color: #6b7280; 
        }
        .calculator-container { 
            background: #1f1f1f; 
            border: 1px solid #50ff96; 
            border-radius: 10px; 
            padding: 15px; 
            margin-top: 20px; 
            box-shadow: 0 3px 10px rgba(80, 255, 150, 0.25); 
            animation: fadeInDown 0.5s ease; 
        }
        .calculator-input { 
            background: #121212; 
            border: 1px solid #50ff96; 
            border-radius: 8px; 
            padding: 10px; 
            color: #d4d4d4; 
            width: 100%; 
            box-shadow: inset 0 0 5px rgba(80, 255, 150, 0.2); 
        }
        .calculator-button { 
            background: #50ff96; 
            color: #0a0a0a; 
            padding: 10px; 
            border-radius: 8px; 
            transition: all 0.3s ease; 
            box-shadow: 0 0 10px rgba(80, 255, 150, 0.4); 
            width: 100%; 
            margin-top: 10px; 
        }
        .calculator-button:hover { 
            background: #40cc7a; 
            box-shadow: 0 0 15px rgba(80, 255, 150, 0.6); 
        }
        .calculator-result { 
            color: #ffffff; 
            margin-top: 10px; 
            font-weight: bold; 
        }
        .footer { 
            text-align: center; 
            color: #6b7280; 
            font-size: 12px; 
            margin-top: 20px; 
            text-shadow: 0 0 5px rgba(80, 255, 150, 0.1); 
        }
        .footer a { 
            color: #50ff96; 
            text-decoration: none; 
            transition: color 0.2s ease; 
        }
        .footer a:hover { 
            color: #40cc7a; 
        }
        .toggle-btn { 
            background: #50ff96; 
            color: #0a0a0a; 
            padding: 10px 14px; 
            border-radius: 10px; 
            transition: all 0.3s ease; 
            box-shadow: 0 0 12px rgba(80, 255, 150, 0.5); 
        }
        .toggle-cylinder-btn:hover { 
            background: #40cc7a; 
            box-shadow: 0 0 18px rgba(80, 255, 150, 0.7); 
            transform: scale(1.05); 
        }
        @keyframes fadeInDown { 
            from { opacity: 0; transform: translateY(-20px); } 
            to { opacity: 1; transform: translateY(0); } 
        }
        @keyframes slideInLeft { 
            from { opacity: 0; transform: translateX(-20px); } 
            to { opacity: 1; transform: translateX(0); } 
        }
        @keyframes slideInRight { 
            from { opacity: 0; transform: translateX(20px); } 
            to { opacity: 1; transform: translateX(0); } 
        }
        @keyframes pulseBorder { 
            0% { box-shadow: 0 0 10px rgba(80, 255, 150, 0.3); } 
            50% { box-shadow: 0 0 15px rgba(80, 255, 150, 0.5); } 
            100% { box-shadow: 0 0 10px rgba(80, 255, 150, 0.3); } 
        }
        @keyframes pulseGlow { 
            0% { transform: scale(1); opacity: 0.8; } 
            50% { transform: scale(1.05); opacity: 1; } 
            100% { transform: scale(1); opacity: 0.8; } 
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar toggle
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = False

st.markdown('<div class="fixed top-4 left-4">', unsafe_allow_html=True)
if st.button("☰ History", key="toggle_sidebar", help="Toggle conversation history", type="primary"):
    st.session_state.sidebar_open = not st.session_state.sidebar_open
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar with calculator
with st.sidebar:
    st.markdown(f'<div class="{"sidebar-visible" if st.session_state.sidebar_open else "sidebar-hidden"}">', unsafe_allow_html=True)
    st.markdown('<h2 class="text-xl font-semibold text-white mb-4">Conversations</h2>', unsafe_allow_html=True)
    conversations = load_conversations()
    today, one_week_ago = datetime.now(), datetime.now() - timedelta(days=7)
    today_convs, last_week_convs = {}, {}
    
    for conv_id, data in conversations.items():
        conv_time = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
        (today_convs if conv_time >= today.replace(hour=0, minute=0, second=0) else last_week_convs)[conv_id] = data
    
    for section, convs in [("Today", today_convs), ("Previous 7 Days", last_week_convs)]:
        if convs:
            st.markdown(f'<h3 class="text-sm font-medium text-gray-500 mt-4">{section}</h3>', unsafe_allow_html=True)
            for conv_id, data in convs.items():
                is_selected = st.session_state.get("selected_conversation") == conv_id
                st.markdown(f'<div class="conversation-item {"selected" if is_selected else ""}">{conv_id}<br><span class="text-xs text-gray-600">{data["timestamp"]}</span></div>', unsafe_allow_html=True)
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("Load", key=f"select_{conv_id}", type="secondary"):
                        st.session_state.selected_conversation = conv_id
                        st.session_state.chat_history = conversations[conv_id]["history"]
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{conv_id}", type="secondary"):
                        delete_conversation(conv_id)
                        if st.session_state.get("selected_conversation") == conv_id:
                            st.session_state.selected_conversation = None
                        st.rerun()
    
    if st.button("New Chat", key="new_conv", type="primary", help="Start a new conversation"):
        st.session_state.selected_conversation = None
        st.session_state.chat_history = []
        st.session_state.conversation_id = f"conv_{int(time.time())}"
        st.session_state.welcome_shown = False
        st.rerun()
    
    # Sidebar Calculator
    st.markdown('<div class="calculator-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="text-lg font-semibold text-white mb-3">🧮 Calculator</h3>', unsafe_allow_html=True)
    calc_input = st.text_input("Expression", placeholder="e.g., 5 + 3 * 2", key="calc_input", help="Enter a math expression")
    if st.button("Calculate", key="calc_submit", help="Evaluate expression", type="primary"):
        try:
            allowed_chars = set("0123456789. +-*/()")
            if all(c in allowed_chars for c in calc_input):
                result = eval(calc_input)
                st.markdown(f'<p class="calculator-result">Result: {result}</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="calculator-result">Error: Invalid characters</p>', unsafe_allow_html=True)
        except ZeroDivisionError:
            st.markdown('<p class="calculator-result">Error: Division by zero</p>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<p class="calculator-result">Error: {str(e)}</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Main chat area
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown("""
    <div class="chat-header">
        <h1 class="text-2xl font-semibold text-white">[💼 Business Proposal Assistant]</h1>
        <p class="text-sm text-gray-500">Powered by OpenRouter</p>
    </div>
""", unsafe_allow_html=True)

# Session state initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{int(time.time())}"
if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False

# Welcome message with graphics
if not st.session_state.chat_history and not st.session_state.welcome_shown:
    welcome = """👋 Welcome to your Business Proposal Assistant!

I specialize in helping with:
- **Marketing strategies**
- **Financial planning**
- **Business development**
- **Startup advice**
- **Operational efficiency**

Ask me anything about running or growing your business!"""
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f'<div class="assistant-message">{welcome}</div>', unsafe_allow_html=True)
    st.session_state.chat_history.append(("assistant", welcome))
    st.session_state.welcome_shown = True

# Chat history
st.markdown('<div class="chat-history">', unsafe_allow_html=True)
for role, message in st.session_state.chat_history:
    with st.chat_message(role, avatar="👤" if role == "user" else "🤖"):
        st.markdown(f'<div class="{role}-message">{message}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Input area
st.markdown('<div class="input-container">', unsafe_allow_html=True)
user_prompt = st.chat_input("Type your business question or proposal idea...")
st.markdown('</div>', unsafe_allow_html=True)

COOLDOWN = 2
if user_prompt:
    if time.time() - st.session_state.last_request_time < COOLDOWN:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown('<div class="assistant-message">Hold up—give me a sec to process that last one.</div>', unsafe_allow_html=True)
    else:
        st.session_state.last_request_time = time.time()
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="user-message">{user_prompt}</div>', unsafe_allow_html=True)
        
        with st.spinner("Crafting your response..."):
            response = generate_response(user_prompt, st.session_state.chat_history) if is_business_related(user_prompt) else "I specialize in business topics. Please ask about marketing, finance, strategy, or related subjects."
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f'<div class="assistant-message">{response}</div>', unsafe_allow_html=True)
            st.session_state.chat_history.append(("user", user_prompt))
            st.session_state.chat_history.append(("assistant", response))
            save_conversation(st.session_state.conversation_id, st.session_state.chat_history)

# Footer
st.markdown('<div class="footer">Powered by OpenRouter • <a href="https://x.com">Follow us on X</a></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
