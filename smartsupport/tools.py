from typing import Optional, List, Dict, Any
from langchain.tools import tool
from pydantic import BaseModel, Field
from database import get_db_session, Customer, Product, Order, OrderItem, OrderStatus
from rag import search_knowledge_base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool
def get_customer_id(email: str) -> Optional[int]:
    """
    Look up customer ID by email address.
    
    Args:
        email: Customer's email address
        
    Returns:
        Customer ID if found, None otherwise
        
    Example:
        get_customer_id("john.doe@email.com") -> 1
    """
    try:
        with get_db_session() as db:
            customer = db.query(Customer).filter(Customer.email == email).first()
            if customer:
                logger.info(f"Found customer ID {customer.id} for email {email}")
                return customer.id
            else:
                logger.info(f"No customer found with email {email}")
                return None
    except Exception as e:
        logger.error(f"Error looking up customer by email: {e}")
        return None


@tool
def get_order_status(order_id: int) -> Dict[str, Any]:
    """
    Get complete order details including status, items, and customer information.
    
    Args:
        order_id: Order ID number
        
    Returns:
        Dictionary with order details, items, and customer info, or error message
        
    Example:
        get_order_status(1005) -> {
            "order_id": 1005,
            "status": "shipped",
            "order_date": "2024-11-15",
            "total_amount": 2799.99,
            "customer": {"name": "John Doe", "email": "john.doe@email.com"},
            "items": [...]
        }
    """
    try:
        with get_db_session() as db:
            order = db.query(Order).filter(Order.id == order_id).first()
            
            if not order:
                return {"error": f"Order #{order_id} not found"}
            
            # Get order items with product details
            items = []
            for order_item in order.order_items:
                items.append({
                    "product_name": order_item.product.name,
                    "quantity": order_item.quantity,
                    "price": order_item.price_at_purchase,
                    "subtotal": order_item.price_at_purchase * order_item.quantity
                })
            
            # Build response
            result = {
                "order_id": order.id,
                "status": order.status.value,
                "order_date": order.order_date.strftime("%Y-%m-%d"),
                "total_amount": order.total_amount,
                "customer": {
                    "name": order.customer.name,
                    "email": order.customer.email,
                    "phone": order.customer.phone
                },
                "items": items,
                "item_count": len(items)
            }
            
            logger.info(f"Retrieved order {order_id} with {len(items)} items")
            return result
            
    except Exception as e:
        logger.error(f"Error retrieving order status: {e}")
        return {"error": f"Error retrieving order: {str(e)}"}


@tool
def list_recent_orders(customer_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    List recent orders for a customer.
    
    Args:
        customer_id: Customer's ID number
        limit: Maximum number of orders to return (default: 5)
        
    Returns:
        List of order summaries, or error message
        
    Example:
        list_recent_orders(1, limit=3) -> [
            {"order_id": 1005, "date": "2024-11-15", "status": "shipped", "total": 2799.99},
            ...
        ]
    """
    try:
        with get_db_session() as db:
            # Verify customer exists
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return [{"error": f"Customer ID {customer_id} not found"}]
            
            # Get recent orders
            orders = (
                db.query(Order)
                .filter(Order.customer_id == customer_id)
                .order_by(Order.order_date.desc())
                .limit(limit)
                .all()
            )
            
            if not orders:
                return [{"message": f"No orders found for customer {customer.name}"}]
            
            # Format results
            results = []
            for order in orders:
                results.append({
                    "order_id": order.id,
                    "date": order.order_date.strftime("%Y-%m-%d"),
                    "status": order.status.value,
                    "total": order.total_amount,
                    "item_count": len(order.order_items)
                })
            
            logger.info(f"Retrieved {len(results)} orders for customer {customer_id}")
            return results
            
    except Exception as e:
        logger.error(f"Error listing recent orders: {e}")
        return [{"error": f"Error retrieving orders: {str(e)}"}]


@tool
def search_products(keyword: str) -> List[Dict[str, Any]]:
    """
    Search for products by keyword in name or description.
    
    Args:
        keyword: Search term (searches in product name and description)
        
    Returns:
        List of matching products with details
        
    Example:
        search_products("RTX 4090") -> [
            {"id": 1, "name": "Apex Gaming PC - RTX 4090 Ultimate", "price": 3999.99, ...},
            {"id": 6, "name": "NVIDIA GeForce RTX 4090 24GB", "price": 1599.99, ...}
        ]
    """
    try:
        with get_db_session() as db:
            # Search in name and description (case-insensitive)
            products = (
                db.query(Product)
                .filter(
                    (Product.name.ilike(f"%{keyword}%")) |
                    (Product.description.ilike(f"%{keyword}%"))
                )
                .all()
            )
            
            if not products:
                return [{"message": f"No products found matching '{keyword}'"}]
            
            # Format results
            results = []
            for product in products:
                results.append({
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "in_stock": product.stock > 0,
                    "stock_quantity": product.stock
                })
            
            logger.info(f"Found {len(results)} products matching '{keyword}'")
            return results
            
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        return [{"error": f"Error searching products: {str(e)}"}]


@tool
def get_customer_orders_summary(email: str) -> Dict[str, Any]:
    """
    Get complete customer profile with recent orders (combines customer lookup and order history).
    
    Args:
        email: Customer's email address
        
    Returns:
        Dictionary with customer info and recent orders
        
    Example:
        get_customer_orders_summary("john.doe@email.com") -> {
            "customer": {"id": 1, "name": "John Doe", ...},
            "recent_orders": [...]
        }
    """
    try:
        with get_db_session() as db:
            # Find customer
            customer = db.query(Customer).filter(Customer.email == email).first()
            
            if not customer:
                return {"error": f"No customer found with email {email}"}
            
            # Get recent orders
            orders = (
                db.query(Order)
                .filter(Order.customer_id == customer.id)
                .order_by(Order.order_date.desc())
                .limit(5)
                .all()
            )
            
            # Format orders
            order_list = []
            for order in orders:
                order_list.append({
                    "order_id": order.id,
                    "date": order.order_date.strftime("%Y-%m-%d"),
                    "status": order.status.value,
                    "total": order.total_amount,
                    "item_count": len(order.order_items)
                })
            
            # Build response
            result = {
                "customer": {
                    "id": customer.id,
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone
                },
                "total_orders": len(orders),
                "recent_orders": order_list
            }
            
            logger.info(f"Retrieved profile for customer {customer.email} with {len(orders)} orders")
            return result
            
    except Exception as e:
        logger.error(f"Error getting customer orders summary: {e}")
        return {"error": f"Error retrieving customer data: {str(e)}"}


@tool
def retrieve_relevant_docs(query: str, k: int = 5) -> str:
    """
    Search knowledge base for relevant information about products, policies, and procedures.
    Use this for general questions about plans, warranties, shipping, troubleshooting, etc.
    
    Args:
        query: Search query about products, policies, or procedures
        k: Number of relevant documents to retrieve (default: 5)
        
    Returns:
        Formatted string with relevant information and source citations
        
    Example:
        retrieve_relevant_docs("What's included in the gaming PC warranty?") ->
        "According to warranty_and_support.md:
        All gaming PCs include a 3-year parts and labor warranty..."
    """
    try:
        # Search knowledge base
        results = search_knowledge_base(query, k=k)
        
        if not results:
            return "No relevant information found in knowledge base."
        
        # Format results with source citations
        formatted_output = []
        seen_sources = set()
        
        for i, result in enumerate(results, 1):
            source_file = result["source"].split("/")[-1].split("\\")[-1]  # Get filename
            content = result["content"].strip()
            
            # Add source header if new source
            if source_file not in seen_sources:
                formatted_output.append(f"\n**Source: {source_file}**")
                seen_sources.add(source_file)
            
            formatted_output.append(f"\n{content}\n")
        
        output = "\n".join(formatted_output)
        logger.info(f"Retrieved {len(results)} relevant documents for query: {query[:50]}...")
        
        return output
        
    except Exception as e:
        logger.error(f"Error retrieving relevant documents: {e}")
        return f"Error searching knowledge base: {str(e)}"


ALL_TOOLS = [
    get_customer_id,
    get_order_status,
    list_recent_orders,
    search_products,
    get_customer_orders_summary,
    retrieve_relevant_docs
]


if __name__ == "__main__":
    print("Testing SQL tools...")
    print("\n1. Get customer ID:")
    print(get_customer_id.invoke({"email": "john.doe@email.com"}))
    
    print("\n2. Search products:")
    print(search_products.invoke({"keyword": "RTX 4090"}))
    
    print("\n3. Get order status:")
    print(get_order_status.invoke({"order_id": 1}))
    
    print("\n\nTesting RAG tool...")
    print("\n4. Retrieve relevant docs:")
    print(retrieve_relevant_docs.invoke({"query": "What gaming PCs do you offer?", "k": 3}))
