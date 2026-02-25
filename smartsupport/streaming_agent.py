import asyncio
from typing import TypedDict, Annotated, Sequence, AsyncGenerator, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from tools import ALL_TOOLS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamingAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    streaming_response: Optional[str]
    is_streaming: bool


class StreamingAgent:
    def __init__(self):
        # Use faster model for low-latency scenarios with more creativity for natural responses
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,  # Increased for more natural, varied responses
            streaming=True,
            max_tokens=150  # Shorter for more conversational responses
        )
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

        # System prompt optimized for natural, human-like voice interactions
        self.system_prompt = """You're Tommy from Stateira Labs - think of yourself as a helpful, friendly person answering the phone, not a formal AI assistant.

Conversation Style:
- Talk like a real person would - use "yeah," "sure," "totally," "hmm"
- Use contractions: "I'm," "we've," "that's," "can't"
- Add natural pauses and fillers: "well," "so," "actually," "you know"
- Show genuine interest: "Oh cool!" "That sounds great!" "Absolutely!"
- Be casual but professional: "Hey there!" instead of "Hello, how may I assist you?"

Keep it Natural:
- 20-30 words max - like real phone conversations
- One main idea per response
- Ask one simple follow-up question
- Use "um" or "let me see" when thinking
- Vary your responses - don't sound scripted

Examples of YOUR voice:
- "Hey! Yeah, I can definitely help with that."
- "Oh, that's interesting! Tell me more about what you're looking for."
- "Hmm, let me check on that for you real quick."
- "Actually, that sounds perfect for what we do!"

Remember: You're having a real conversation with someone who called in. Be human, be helpful, be yourself!"""

        self.agent_graph = self._create_streaming_graph()

    def _create_streaming_graph(self):
        """Create LangGraph with streaming capabilities"""
        workflow = StateGraph(StreamingAgentState)

        workflow.add_node("agent", self._call_streaming_model)
        workflow.add_node("tools", ToolNode(ALL_TOOLS))
        workflow.set_entry_point("agent")

        workflow.add_conditional_edges(
            "agent",
            self._should_continue_streaming,
            {
                "tools": "tools",
                "end": END
            }
        )
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    async def _call_streaming_model(self, state: StreamingAgentState) -> StreamingAgentState:
        """Call LLM with streaming support"""
        messages = state["messages"]

        # Add system message if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=self.system_prompt)] + messages

        # Stream the response
        response_content = ""
        async for chunk in self.llm_with_tools.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                response_content += chunk.content

        # Create complete response message
        response = AIMessage(content=response_content)

        # Check for tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            # If we need tools, don't stream yet
            return {"messages": [response], "is_streaming": False}

        return {
            "messages": [response],
            "streaming_response": response_content,
            "is_streaming": True
        }

    def _should_continue_streaming(self, state: StreamingAgentState) -> str:
        """Determine if we need to call tools or can end"""
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    async def stream_response(self, query: str) -> AsyncGenerator[str, None]:
        """Stream agent response token by token"""
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "streaming_response": None,
            "is_streaming": False
        }

        try:
            # Check for quick cached responses first
            quick_response = self._get_quick_response(query)
            if quick_response:
                yield quick_response
                return

            # Start streaming response
            messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=query)]

            response_buffer = ""
            sentence_buffer = ""

            async for chunk in self.llm_with_tools.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    response_buffer += content
                    sentence_buffer += content

                    # Yield content immediately for parallel TTS
                    yield content

                    # Check if we have a complete sentence for early TTS start
                    if any(punct in sentence_buffer for punct in ['.', '!', '?']):
                        logger.debug(f"Complete sentence ready for TTS: {sentence_buffer}")
                        sentence_buffer = ""

            logger.info(f"Streaming completed. Total response: {response_buffer[:100]}...")

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield "I'm sorry, I'm experiencing technical difficulties. Please try again."

    async def get_response(self, query: str) -> str:
        """Get complete response (non-streaming fallback)"""
        try:
            # Check for quick responses
            quick_response = self._get_quick_response(query)
            if quick_response:
                return quick_response

            # Use the graph for complex queries
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "streaming_response": None,
                "is_streaming": False
            }

            result = await self.agent_graph.ainvoke(initial_state)
            return result["messages"][-1].content

        except Exception as e:
            logger.error(f"Error getting agent response: {e}")
            return "I'm sorry, I'm experiencing technical difficulties. Please try again."

    def _get_quick_response(self, query: str) -> Optional[str]:
        """Check for quick cached responses to common queries - now with natural language"""
        query_lower = query.lower().strip()

        # Natural, conversational responses with variety
        import random

        quick_responses = {
            "hello": [
                "Hey there! What's up?",
                "Hi! How's it going?",
                "Hey! What can I help you with?",
                "Oh hey! How can I help?",
                "Hello! What brings you to Stateira Labs today?"
            ],
            "hi": [
                "Hi! What's going on?",
                "Hey! How are you doing?",
                "Hi there! What can I do for you?",
                "Oh hi! What's up?"
            ],
            "hey": [
                "Hey! What's up?",
                "Hey there! How can I help?",
                "Oh hey! What's going on?",
                "Hey! How are you?"
            ],
            "thank you": [
                "Yeah, totally! Anything else I can help with?",
                "Of course! Is there anything else?",
                "You got it! What else can I do for you?",
                "No problem! Need anything else?"
            ],
            "thanks": [
                "You bet! Anything else?",
                "Sure thing! What else?",
                "Absolutely! Need help with anything else?",
                "No worries! Anything else I can do?"
            ],
            "bye": [
                "Alright, take care!",
                "See you later! Have a good one!",
                "Bye! Thanks for calling!",
                "Talk to you later!"
            ],
            "goodbye": [
                "See ya! Have a great day!",
                "Bye! Take it easy!",
                "Later! Thanks for calling Stateira Labs!",
                "Goodbye! Have an awesome day!"
            ],
            "how are you": [
                "I'm doing great! How about you?",
                "Pretty good! What's up with you?",
                "I'm awesome! What brings you here today?",
                "Doing well! How can I help you out?"
            ],
            "what's up": [
                "Not much! What about you?",
                "Just helping folks out! What's going on?",
                "Same old! What brings you by?",
                "Just here helping people! What's up with you?"
            ]
        }

        # Check for matches and return a random variation
        for trigger, responses in quick_responses.items():
            if trigger in query_lower:
                response = random.choice(responses)
                logger.info(f"Using quick response for: {query} -> {response}")
                return response

        return None

    async def parallel_llm_tts(self, query: str, audio_service) -> tuple[str, str]:
        """Generate LLM response and TTS audio in parallel"""
        import asyncio

        # Start both operations concurrently
        async def collect_streaming_response():
            full_response = ""
            async for chunk in self.stream_response(query):
                full_response += chunk
            return full_response

        async def generate_audio_from_stream():
            # Create a generator that yields text as it comes in
            async def text_generator():
                async for chunk in self.stream_response(query):
                    yield chunk

            # This would need to be implemented in audio_service
            return await audio_service.parallel_llm_tts_generation(
                text_generator(),
                "https://your-app-url.com"
            )

        try:
            # Run both operations in parallel
            response_task = asyncio.create_task(collect_streaming_response())
            audio_task = asyncio.create_task(generate_audio_from_stream())

            # Wait for both to complete
            response, audio_url = await asyncio.gather(response_task, audio_task)

            return response, audio_url

        except Exception as e:
            logger.error(f"Error in parallel LLM-TTS: {e}")
            # Fallback to sequential processing
            response = await self.get_response(query)
            return response, None


# Global streaming agent instance
streaming_agent = StreamingAgent()