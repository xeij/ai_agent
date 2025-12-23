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

SYSTEM_PROMPT = """You are a helpful customer service AI assistant for SmartSupport, a computer retail company specializing in gaming PCs, workstations, and components.

Your role is to help customers with:
1. **Personalized queries** requiring customer data (order status, account info, purchase history)
2. **General queries** about products, policies, warranties, shipping, troubleshooting, etc.

## Guidelines:

### For Personalized Queries:
- **Always verify customer identity** before accessing personal data
- Ask for email address or order ID if not provided
- Use SQL tools: get_customer_id, get_order_status, list_recent_orders, search_products, get_customer_orders_summary
- Be specific and accurate with order details

### For General Queries:
- Use the retrieve_relevant_docs tool to search the knowledge base
- **Never hallucinate** product details, prices, or policies
- **Always cite sources** when using knowledge base information (e.g., "According to our warranty policy...")
- If information isn't in the knowledge base, say so honestly

### Response Style:
- Be professional, friendly, and concise
- Use clear formatting (bullet points, numbered lists)
- Provide specific details (prices, dates, specifications)
- Offer next steps or additional help

### Error Handling:
- If order/customer not found, politely ask for verification
- If query is ambiguous, ask clarifying questions
- If you can't help, offer to escalate to human support

### Security:
- Never share customer data without verification
- Don't make up order numbers or customer information
- Protect sensitive information

Remember: You have access to both structured customer data (SQL) and unstructured knowledge base (RAG). Use the appropriate tools based on the query type.
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
