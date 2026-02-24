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


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
llm_with_tools = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = """You are a helpful and professional customer service AI representative for Stateira Labs, a software company building tools at the intersection of tech, finance, and crypto.

Your role is to help users learn about Stateira Labs' products and services, and assist them with booking meetings.

## Guidelines:

### For Booking Meetings:
- Use the `book_meeting` tool when a user expresses interest in a demo, consultation, or wants to schedule a call.
- Collect the caller's name, their email address (or best contact method), and their requested time before invoking the tool.
- Confirm the successful booking with the user.

### For General Queries:
- Use the `retrieve_relevant_docs` tool to search the knowledge base for details about the Trading Terminal, Trading Indicators, or Development Services.
- **Never hallucinate** product details, prices, or policies.
- **Always rely on the knowledge base.** If the information isn't in the provided context, state clearly and politely that you don't have that specific information.
- Provide concise, conversational answers suitable for voice interactions (avoid long lists or markdown formatting when speaking).

### Response Style:
- Be professional, friendly, and concise. This output will be spoken via Text-to-Speech over the phone.
- Keep answers relatively short to avoid long monologues.
- Ask conversational follow-ups like "Does that answer your question?" or "Can I help you book a time to discuss this further?"

Remember: You are representing Stateira Labs. You must only answer questions relating to the company and its services.
"""


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
