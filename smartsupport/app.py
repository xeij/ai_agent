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
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    .example-query {
        background-color: #F1F5F9;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        cursor: pointer;
        border-left: 4px solid #3B82F6;
    }
    .example-query:hover {
        background-color: #E2E8F0;
    }
    .stChatMessage {
        background-color: #FFFFFF;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
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


def display_sidebar():
    with st.sidebar:
        st.markdown("### SmartSupport AI")
        st.markdown("Your intelligent customer service assistant")
        
        st.markdown("---")
        
        st.markdown("### Example Queries")
        
        st.markdown("**Personalized Queries:**")
        personalized_examples = [
            "What's the status of order #1?",
            "Show my recent orders (email: john.doe@email.com)",
            "Do you have any RTX 4090 systems in stock?",
        ]
        
        for example in personalized_examples:
            if st.button(example, key=f"personal_{example}", use_container_width=True):
                st.session_state.example_query = example
        
        st.markdown("**General Queries:**")
        general_examples = [
            "What gaming PCs do you offer?",
            "Tell me about your warranty coverage",
            "What's your return policy?",
            "How does component upgrade work?",
            "What financing options are available?",
        ]
        
        for example in general_examples:
            if st.button(example, key=f"general_{example}", use_container_width=True):
                st.session_state.example_query = example
        
        st.markdown("---")
        
        # Clear conversation button
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        


def main():
    # Initialize system
    if not initialize_system():
        st.stop()
    
    # Initialize session state
    initialize_session_state()
    
    # Display sidebar
    display_sidebar()
    
    # Main content area
    st.markdown('<div class="main-header">SmartSupport AI Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Hybrid AI customer service powered by SQL + RAG</div>', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle example query from sidebar
    if "example_query" in st.session_state:
        query = st.session_state.example_query
        del st.session_state.example_query
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # Generate and stream response
        with st.chat_message("assistant"):
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
            st.markdown(prompt)
        
        # Generate and stream response
        with st.chat_message("assistant"):
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
