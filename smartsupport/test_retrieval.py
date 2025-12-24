from rag import query_knowledge_base
import logging

# Configure logging to see details
logging.basicConfig(level=logging.INFO)

query = "Return policy?"
print(f"Testing query: '{query}'")

try:
    results = query_knowledge_base(query)
    
    if results:
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print("-" * 50)
            print(result)
            print("-" * 50)
    else:
        print("\nNo results found.")
        
except Exception as e:
    print(f"\nError: {e}")
