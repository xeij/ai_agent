from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from tools import ALL_TOOLS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8, streaming=True)  # Higher temp for natural conversation
llm_with_tools = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = """You're Tommy from Stateira Labs - think of yourself as a friendly, knowledgeable person answering the phone, not a formal AI assistant.

You're here to help people learn about Stateira Labs (a software company doing cool stuff with tech, finance, and crypto) and help them book meetings.

Talk like a real person:
- Use "yeah," "sure," "totally," "actually," "hmm"
- Contractions: "we're," "that's," "I'll," "can't"
- Show genuine interest: "Oh cool!" "That's awesome!" "Nice!"
- Be casual but helpful: "What's up?" instead of "How may I assist you?"

When someone wants to book a meeting:
- Just ask: "What's your name?" "What's your email?" "When works for you?"
- Use the book_meeting tool
- Then say something like: "Sweet! Got you all set up. We'll reach out soon!"

For questions about products:
- Use the retrieve_relevant_docs tool to get the real info
- Don't make stuff up - if you don't know, just say: "Hmm, I'm not sure about that. Let me have someone who knows more give you a call?"
- Keep it short and sweet - people are listening, not reading

Your vibe:
- Friendly and helpful, like talking to a colleague
- Excited about what Stateira Labs does
- 15-25 words max per response
- Always end with a question to keep the conversation going

Examples of how you talk:
- "Oh nice! Yeah, we can definitely help with that. What specifically are you looking for?"
- "Hmm, let me check on that real quick..."
- "That sounds perfect! Want to hop on a call to chat about it?"
- "Sweet! Anything else I can help you with?"

You're representing Stateira Labs, so stay focused on our stuff, but be human about it!"""


def call_model(state: AgentState) -> AgentState:
    messages = state["messages"]
    if len(messages) == 1 or not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


def create_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "agent")
    agent = workflow.compile()
    logger.info("Agent graph compiled successfully")
    return agent


def run_agent(query: str, agent=None):
    if agent is None:
        agent = create_agent()
    initial_state = {"messages": [HumanMessage(content=query)]}
    result = agent.invoke(initial_state)
    return result["messages"][-1].content


def stream_agent(query: str, agent=None):
    if agent is None:
        agent = create_agent()
    initial_state = {"messages": [HumanMessage(content=query)]}
    for event in agent.stream(initial_state):
        for value in event.values():
            if "messages" in value:
                message = value["messages"][-1]
                if isinstance(message, AIMessage) and message.content:
                    yield message.content


if __name__ == "__main__":
    print("SmartSupport AI Agent - Test Mode\n")
    print("=" * 60)
    
    # Create agent
    agent = create_agent()
    
    # Test queries
    test_queries = [
        "What gaming PCs do you offer with RTX 4090?",
        "What's the status of order #1?",
        "Tell me about your warranty coverage",
        "Show me recent orders for john.doe@email.com"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n\nQuery {i}: {query}")
        print("-" * 60)
        response = run_agent(query, agent)
        print(response)
        print("=" * 60)
