import os
from typing import List
from pathlib import Path
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = "./knowledge_base"
CHROMA_DB_DIR = "./chroma_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"


def load_and_split_documents() -> List:
    try:
        logger.info(f"Loading documents from {KNOWLEDGE_BASE_DIR}")
        
        # Load all markdown files
        loader = DirectoryLoader(
            KNOWLEDGE_BASE_DIR,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} documents")
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        splits = text_splitter.split_documents(documents)
        logger.info(f"Split into {len(splits)} chunks")
        
        return splits
    
    except Exception as e:
        logger.error(f"Error loading and splitting documents: {e}")
        raise


def create_vector_store(documents: List) -> Chroma:
    try:
        logger.info("Creating embeddings and vector store")
        
        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        
        # Create Chroma vector store with persistence
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=CHROMA_DB_DIR,
            collection_name="smartsupport_knowledge"
        )
        
        logger.info(f"Vector store created with {vectorstore._collection.count()} documents")
        return vectorstore
    
    except Exception as e:
        logger.error(f"Error creating vector store: {e}")
        raise


def get_retriever(k: int = 5):
    try:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        
        # Load existing vector store
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings,
            collection_name="smartsupport_knowledge"
        )
        
        # Create retriever
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        
        return retriever
    
    except Exception as e:
        logger.error(f"Error getting retriever: {e}")
        raise


def ingest_knowledge_base() -> None:
    # Check if Chroma DB already exists
    chroma_path = Path(CHROMA_DB_DIR)
    if chroma_path.exists() and any(chroma_path.iterdir()):
        logger.info("Chroma database already exists. Skipping ingestion.")
        logger.info("To re-ingest, delete the chroma_db directory.")
        return
    
    logger.info("Starting knowledge base ingestion...")
    
    # Load and split documents
    documents = load_and_split_documents()
    
    # Create vector store
    vectorstore = create_vector_store(documents)
    
    logger.info("Knowledge base ingestion completed successfully!")
    logger.info(f"Total chunks indexed: {vectorstore._collection.count()}")


def search_knowledge_base(query: str, k: int = 5) -> List[dict]:
    try:
        retriever = get_retriever(k=k)
        # Use invoke() instead of get_relevant_documents() which is deprecated/removed
        results = retriever.invoke(query)
        
        # Format results
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "score": getattr(doc, "score", None)
            })
        
        return formatted_results
    
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return []


if __name__ == "__main__":
    ingest_knowledge_base()
