# Customer Support AI Agent

A hybrid customer support agent demonstrating production-grade AI agent architecture. Combines SQL database queries with RAG (Retrieval-Augmented Generation) to handle both personalized account queries and general product information.

Architecture Overview

This project implements a stateful AI agent using LangGraph that intelligently routes between two data sources:

**Structured data (SQL)** - Customer accounts, orders, product inventory  
**Unstructured data (RAG)** - Product documentation, policies, support guides

The agent automatically determines which tools to use based on the user's query, preventing hallucinations by grounding responses in actual data rather than relying on the LLM's training.


Agent Workflow

The LangGraph workflow follows a simple pattern:

1. **User query** → Agent receives the question
2. **Intent classification** → LLM analyzes whether this needs database access or knowledge base search
3. **Tool execution** → Appropriate tools are called (SQL queries or vector search)
4. **Response synthesis** → LLM generates a natural response using the retrieved data

For knowledge base queries, the agent always cites source documents to maintain transparency and prevent making things up.

Components

**agent.py** - LangGraph state machine with conditional routing. Uses GPT-4o-mini for cost-effective production deployment.

**tools.py** - Six LangChain tools:
- 5 SQL tools (customer lookup, order status, product search, etc.)
- 1 RAG tool (knowledge base search with source citations)

**database.py** - SQLAlchemy models for customers, products, orders, and order items. Uses context managers for safe session handling.

**rag.py** - Document ingestion pipeline using RecursiveCharacterTextSplitter (1000 char chunks, 200 overlap) and Chroma for persistent vector storage.

**app.py** - Streamlit interface with streaming responses and conversation history.

Data Layer

**Database** - SQLite with 12 sample customers, 18 computer products (gaming PCs, workstations, components), and 25 orders. All queries use parameterized SQLAlchemy ORM to prevent SQL injection.

**Knowledge Base** - 10 markdown documents (~15,000 words) covering:
- Product catalogs (gaming PCs, workstations)
- Policies (warranty, returns, upgrades, shipping)
- Services (custom builds, bulk orders, financing)
- Support (troubleshooting, FAQs)

Documents are embedded using OpenAI's text-embedding-3-small and stored in Chroma for similarity search.

Example Interactions

**Personal query**: "What's the status of order #1?"  
 Agent calls `get_order_status(1)` -> Returns order details from database

**General query**: "What gaming PCs do you offer?"  
 Agent calls `retrieve_relevant_docs("gaming PCs")` -> Searches knowledge base -> Cites gaming_pc_series.md

**Mixed query**: "Do you have RTX 4090 systems in stock?"  
 Agent calls `search_products("RTX 4090")` -> Returns inventory from database
