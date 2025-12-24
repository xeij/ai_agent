import streamlit as st
import os
from dotenv import load_dotenv
from agent import create_agent, stream_agent
from rag import ingest_knowledge_base
from seed_data import seed_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
st.set_page_config(
    page_title="SmartSupport AI Agent",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #000000;
        color: #e0e0e0;
    }
    
    .stApp {
        background-color: #000000;
    }
    
    /* Sidebar - hide completely */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .css-1d391kg {
        display: none !important;
    }
    
    /* Header */
    .main-header {
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        margin: 2rem 0 0.5rem 0;
        letter-spacing: -0.5px;
    }
    
    .sub-header {
        text-align: center;
        font-size: 1rem;
        color: #808080;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Hide markdown header anchor links */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
    }
    
    .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {
        display: none !important;
    }
    
    
    /* Chat messages - base style */
    .stChatMessage {
        background-color: #0f0f0f !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 4px !important;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Hide chat avatars/icons - comprehensive */
    .stChatMessage [data-testid="chatAvatarIcon"] {
        display: none !important;
    }
    
    .stChatMessage img {
        display: none !important;
    }
    
    .stChatMessage svg {
        display: none !important;
    }
    
    [data-testid="stChatMessageAvatarContainer"] {
        display: none !important;
    }
    
    .stChatMessage > div:first-child {
        display: none !important;
    }
    
    /* Hide the avatar column completely */
    .stChatMessage [class*="avatar"] {
        display: none !important;
    }
    
    /* User messages - use :has() selector for robustness */
    .stChatMessage:has(.user-message-marker) {
        background-color: #1a1a1a !important;
        border-left: 3px solid #3a3a3a !important;
    }
    
    /* Assistant messages - use :has() selector for robustness */
    .stChatMessage:has(.assistant-message-marker) {
        background-color: #0a0a0a !important;
        border-left: 3px solid #2a2a2a !important;
    }
    
    .stChatMessage > div {
        background-color: transparent !important;
    }
    
    .stChatMessage p {
        color: #e0e0e0 !important;
    }
    
    .stChatMessage code {
        background-color: #252525 !important;
        color: #e0e0e0 !important;
        padding: 2px 6px;
        border-radius: 3px;
    }
    
    .stChatMessage pre {
        background-color: #1a1a1a !important;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #1a1a1a;
        color: #ffffff;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background-color: #2a2a2a;
        border-color: #4a4a4a;
    }
    
    /* Chat input */
    .stChatInput {
        background-color: #0f0f0f !important;
    }
    
    .stChatInput > div {
        background-color: #0f0f0f !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 4px !important;
    }
    
    .stChatInput input {
        background-color: #0f0f0f !important;
        color: #e0e0e0 !important;
        border-radius: 4px !important;
    }
    
    .stChatInput textarea {
        background-color: #0f0f0f !important;
        color: #e0e0e0 !important;
        border: none !important;
    }
    
    .stChatInput input::placeholder,
    .stChatInput textarea::placeholder {
        color: #606060 !important;
    }
    
    /* Dividers */
    hr {
        border-color: #2a2a2a;
        margin: 1.5rem 0;
    }
    
    /* Remove any blue tints */
    .stApp > header {
        background-color: #000000 !important;
    }
    
    [data-testid="stHeader"] {
        background-color: #000000 !important;
    }
    
    /* Fix bottom section */
    .stApp > footer {
        background-color: #000000 !important;
    }
    
    [data-testid="stBottom"] {
        background-color: #000000 !important;
    }
    
    [data-testid="stBottomBlockContainer"] {
        background-color: #000000 !important;
    }
    
    /* Fix any remaining containers */
    [data-testid="stVerticalBlock"] {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)


def initialize_system():
    try:
        # Check for OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            st.error("⚠️ OPENAI_API_KEY not found in environment variables!")
            st.info("Please create a .env file with your OpenAI API key:")
            st.code("OPENAI_API_KEY=your_key_here")
            st.stop()
        
        # Seed database if needed
        with st.spinner("Initializing database..."):
            seed_database()
        
        # Ingest knowledge base if needed
        with st.spinner("Initializing knowledge base..."):
            ingest_knowledge_base()
        
        logger.info("System initialized successfully")
        return True
        
    except Exception as e:
        st.error(f"Error initializing system: {e}")
        logger.error(f"Initialization error: {e}")
        return False


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        with st.spinner("Loading AI agent..."):
            st.session_state.agent = create_agent()



def display_example_queries():
    """Display example queries in the center when conversation is empty"""
    st.markdown("")
    st.markdown("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Try asking:")
        st.markdown("")
        
        examples = [
            "Status of order #1?",
            "Orders for john.doe@email.com",
            "RTX 4090 in stock?",
            "Gaming PCs available?",
            "Warranty coverage?",
            "Return policy?",
            "Financing options?",
        ]
        
        for example in examples:
            if st.button(example, key=f"center_{example}", use_container_width=True):
                st.session_state.example_query = example
                st.rerun()
        


def main():
    if not initialize_system():
        st.stop()
    
    initialize_session_state()
    
    st.markdown('<div class="main-header">SmartSupport AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Customer Service Agent</div>', unsafe_allow_html=True)
    
    # Clear chat button (only show if there are messages)
    if len(st.session_state.messages) > 0:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
    
    # Show example queries in center if no messages
    if len(st.session_state.messages) == 0:
        display_example_queries()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown('<div class="user-message-marker" style="display:none;"></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="assistant-message-marker" style="display:none;"></div>', unsafe_allow_html=True)
            st.markdown(message["content"])
    
    # Handle example query from sidebar
    if "example_query" in st.session_state:
        query = st.session_state.example_query
        del st.session_state.example_query
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown('<div class="user-message-marker" style="display:none;"></div>', unsafe_allow_html=True)
            st.markdown(query)
        
        # Generate and stream response
        with st.chat_message("assistant"):
            st.markdown('<div class="assistant-message-marker" style="display:none;"></div>', unsafe_allow_html=True)
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Stream response from agent
                for chunk in stream_agent(query, st.session_state.agent):
                    full_response = chunk
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                error_msg = f"I apologize, but I encountered an error: {str(e)}\n\nPlease try again or contact support if the issue persists."
                message_placeholder.markdown(error_msg)
                full_response = error_msg
                logger.error(f"Error processing query: {e}")
        
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask me about orders, products, policies, or anything else..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown('<div class="user-message-marker" style="display:none;"></div>', unsafe_allow_html=True)
            st.markdown(prompt)
        
        # Generate and stream response
        with st.chat_message("assistant"):
            st.markdown('<div class="assistant-message-marker" style="display:none;"></div>', unsafe_allow_html=True)
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Stream response from agent
                for chunk in stream_agent(prompt, st.session_state.agent):
                    full_response = chunk
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                error_msg = f"I apologize, but I encountered an error: {str(e)}\n\nPlease try again or contact support if the issue persists."
                message_placeholder.markdown(error_msg)
                full_response = error_msg
                logger.error(f"Error processing query: {e}")
        
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()


if __name__ == "__main__":
    main()
