# SmartSupport AI Agent

This project implements a production-grade customer support agent capable of handling complex queries by intelligently routing between structured database records and unstructured knowledge base documents.

Combining SQL databases with Retrieval-Augmented Generation (RAG) allows the agent to provide grounded, accurate responses that traditional large language models cannot achieve on their own. It can check real-time inventory and order status just as easily as it can explain return policies or troubleshoot technical issues.

## Technical Architecture

The system is built on a hybrid architecture designed to eliminate hallucinations:

### 1. The Decision Engine (LangGraph)
At the core is a stateful graph that acts as the agent's brain. Instead of a simple linear chain, the agent determines its own path based on the user's intent. It analyzes the incoming query and decides whether to consulting the SQL database, search the knowledge base, or do both.

### 2. Structured Data Layer (SQL)
For precise data like inventory counts, order status, and customer details, the agent uses a suite of SQL tools. It queries a relational database to fetch exact numbers and records. This ensures that when a user asks "Is the RTX 4090 in stock?", the answer is based on actual inventory rows, not a guess.

### 3. Unstructured Data Layer (RAG)
For qualitative questions about policies, product features, and troubleshooting, the agent effectively "reads" a library of markdown documents.
- **Ingestion:** Documents are split into 1000-character chunks and embedded using OpenAI's embedding models.
- **Storage:** These embeddings are stored in a Chroma vector database.
- **Retrieval:** When a user asks about a return policy, the system performs a semantic search to find the most relevant paragraphs and feeds them to the AI as context.

## Key Features

**Real-Time Order Tracking**
Users can ask for the status of specific orders (e.g., "Status of order #1?"). The agent queries the `orders` table and returns the current status, date, and total amount.

**Intelligent Product Search**
The agent mimics a knowledgeable sales representative. It can search for products by name, category, or price range. It understands context, allowing users to ask "Do you have any gaming PCs under $2000?"

**Policy & Support Knowledge**
By indexing internal documentation, the agent provides accurate answers regarding shipping times, return windows, warranty coverage, and technical support procedures. It cites the specific policy documents it used to formulate its answer.

**Contextual Memory**
The conversation history is maintained, allowing for back-and-forth dialogue. If a user asks "How much is it?" immediately after asking about a specific computer, the agent understands which product is being discussed.

## How It Works Under the Hood

When a message is received, the following process occurs:

1.  **Classification:** The system prompt analyzes the user's input to determine if they need specific data (Tool Call) or general conversation.
2.  **Routing:**
    - If the user needs data, the agent selects the appropriate tool (e.g., `lookup_order` or `search_knowledge_base`).
    - If the user is just saying "hello", it skips the tools and responds directly.
3.  **Execution:** The selected tool runs.
    - SQL tools execute safe, parameterized queries against the SQLite database.
    - RAG tools perform a similarity search against the Chroma vector store.
4.  **Synthesis:** The tool outputs (raw data or document snippets) are fed back to the Large Language Model (GPT-4o-mini), which synthesizes a natural, helpful response for the user.

## Setup and Installation

**Prerequisites:**
- Python 3.10+
- OpenAI API Key

**Installation:**
1. Clone the repository and navigate to the project folder.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file and add your key: `OPENAI_API_KEY=your_key_here`
4. Run the application: `streamlit run app.py`

The system will automatically initialize the database with seed data and ingest the knowledge base documents upon the first run.
