"""
Populates the database with realistic fake data:
- 12 customers with varied profiles
- 18 computer products (gaming PCs, workstations, components, peripherals)
- 25 orders with realistic statuses and order items
"""

from datetime import datetime, timedelta
import random
from database import init_db, get_db_session, Customer, Product, Order, OrderItem, OrderStatus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_customers(db):
    """Seed customer data"""
    customers_data = [
        {"name": "John Doe", "email": "john.doe@email.com", "phone": "555-0101"},
        {"name": "Jane Smith", "email": "jane.smith@email.com", "phone": "555-0102"},
        {"name": "Michael Johnson", "email": "michael.j@email.com", "phone": "555-0103"},
        {"name": "Emily Davis", "email": "emily.davis@email.com", "phone": "555-0104"},
        {"name": "Robert Brown", "email": "robert.brown@email.com", "phone": "555-0105"},
        {"name": "Sarah Wilson", "email": "sarah.wilson@email.com", "phone": "555-0106"},
        {"name": "David Martinez", "email": "david.m@email.com", "phone": "555-0107"},
        {"name": "Lisa Anderson", "email": "lisa.anderson@email.com", "phone": "555-0108"},
        {"name": "James Taylor", "email": "james.taylor@email.com", "phone": "555-0109"},
        {"name": "Jennifer Thomas", "email": "jennifer.t@email.com", "phone": "555-0110"},
        {"name": "William Garcia", "email": "william.garcia@email.com", "phone": "555-0111"},
        {"name": "Amanda Rodriguez", "email": "amanda.r@email.com", "phone": "555-0112"},
    ]
    
    customers = []
    for data in customers_data:
        customer = Customer(**data)
        db.add(customer)
        customers.append(customer)
    
    db.flush()
    logger.info(f"Seeded {len(customers)} customers")
    return customers


def seed_products(db):
    """Seed product catalog with gaming PCs, workstations, components, and peripherals"""
    products_data = [
        # Gaming PCs
        {
            "name": "Apex Gaming PC - RTX 4090 Ultimate",
            "description": "Intel i9-14900K, RTX 4090 24GB, 64GB DDR5, 2TB NVMe SSD, Liquid Cooling, RGB",
            "price": 3999.99,
            "stock": 5
        },
        {
            "name": "Titan Gaming PC - RTX 4080",
            "description": "Intel i7-14700K, RTX 4080 16GB, 32GB DDR5, 1TB NVMe SSD, AIO Cooling",
            "price": 2799.99,
            "stock": 12
        },
        {
            "name": "Vortex Gaming PC - RTX 4070 Ti",
            "description": "AMD Ryzen 9 7900X, RTX 4070 Ti 12GB, 32GB DDR5, 1TB NVMe SSD",
            "price": 2199.99,
            "stock": 18
        },
        
        # Workstations
        {
            "name": "ProStation Creator - RTX 4090",
            "description": "Intel Xeon W-2295, RTX 4090 24GB, 128GB ECC RAM, 4TB NVMe RAID, Certified for Adobe/DaVinci",
            "price": 5499.99,
            "stock": 3
        },
        {
            "name": "Studio Workstation - RTX A5000",
            "description": "AMD Threadripper PRO 5975WX, RTX A5000 24GB, 64GB ECC RAM, 2TB NVMe SSD",
            "price": 4299.99,
            "stock": 7
        },
        
        # Components - GPUs
        {
            "name": "NVIDIA GeForce RTX 4090 24GB",
            "description": "Flagship GPU, 16384 CUDA cores, boost clock 2.52GHz, DLSS 3.0",
            "price": 1599.99,
            "stock": 8
        },
        {
            "name": "NVIDIA GeForce RTX 4070 Ti 12GB",
            "description": "High-performance GPU, 7680 CUDA cores, boost clock 2.61GHz",
            "price": 799.99,
            "stock": 15
        },
        {
            "name": "AMD Radeon RX 7900 XTX 24GB",
            "description": "RDNA 3 architecture, 96 compute units, 2.5GHz boost clock",
            "price": 999.99,
            "stock": 10
        },
        
        # Components - CPUs
        {
            "name": "Intel Core i9-14900K",
            "description": "24 cores (8P+16E), 32 threads, up to 6.0GHz, LGA1700",
            "price": 589.99,
            "stock": 20
        },
        {
            "name": "AMD Ryzen 9 7950X",
            "description": "16 cores, 32 threads, up to 5.7GHz, AM5 socket",
            "price": 549.99,
            "stock": 18
        },
        
        # Components - RAM
        {
            "name": "Corsair Vengeance DDR5 64GB (2x32GB) 6000MHz",
            "description": "High-performance DDR5 memory kit, RGB, Intel XMP 3.0",
            "price": 249.99,
            "stock": 30
        },
        {
            "name": "G.Skill Trident Z5 RGB 32GB (2x16GB) 6400MHz",
            "description": "Premium DDR5 RAM, low latency CL32, RGB lighting",
            "price": 159.99,
            "stock": 25
        },
        
        # Storage
        {
            "name": "Samsung 990 PRO 2TB NVMe SSD",
            "description": "PCIe 4.0, 7450MB/s read, 6900MB/s write, 5-year warranty",
            "price": 179.99,
            "stock": 40
        },
        
        # Peripherals
        {
            "name": "Logitech G Pro X Superlight Wireless Mouse",
            "description": "Ultra-lightweight 63g, HERO 25K sensor, 70-hour battery",
            "price": 159.99,
            "stock": 50
        },
        {
            "name": "Corsair K70 RGB Mechanical Keyboard",
            "description": "Cherry MX switches, per-key RGB, aluminum frame, USB passthrough",
            "price": 179.99,
            "stock": 35
        },
        {
            "name": "LG UltraGear 27\" 4K 144Hz Gaming Monitor",
            "description": "27\" IPS, 4K 3840x2160, 144Hz, 1ms, G-Sync Compatible, HDR400",
            "price": 599.99,
            "stock": 15
        },
        {
            "name": "HyperX Cloud III Wireless Gaming Headset",
            "description": "2.4GHz wireless, 120-hour battery, 53mm drivers, detachable mic",
            "price": 169.99,
            "stock": 28
        },
        {
            "name": "Elgato Stream Deck MK.2",
            "description": "15 customizable LCD keys, streaming control, macro shortcuts",
            "price": 149.99,
            "stock": 22
        },
    ]
    
    products = []
    for data in products_data:
        product = Product(**data)
        db.add(product)
        products.append(product)
    
    db.flush()
    logger.info(f"Seeded {len(products)} products")
    return products


def seed_orders(db, customers, products):
    """Seed orders with realistic data"""
    statuses = [OrderStatus.PENDING, OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]
    status_weights = [0.15, 0.25, 0.55, 0.05]  # Most orders are delivered
    
    orders = []
    order_items_list = []
    
    # Create 25 orders
    for i in range(25):
        # Random customer
        customer = random.choice(customers)
        
        # Random date within last 90 days
        days_ago = random.randint(0, 90)
        order_date = datetime.utcnow() - timedelta(days=days_ago)
        
        # Status based on order age (older orders more likely to be delivered)
        if days_ago > 14:
            status = random.choices([OrderStatus.DELIVERED, OrderStatus.CANCELLED], weights=[0.95, 0.05])[0]
        elif days_ago > 7:
            status = random.choices([OrderStatus.SHIPPED, OrderStatus.DELIVERED], weights=[0.4, 0.6])[0]
        else:
            status = random.choices(statuses, weights=status_weights)[0]
        
        # Create order (total_amount will be calculated after adding items)
        order = Order(
            customer_id=customer.id,
            order_date=order_date,
            status=status,
            total_amount=0.0  # Will be updated
        )
        db.add(order)
        db.flush()  # Get order ID
        
        # Add 1-4 items to order
        num_items = random.randint(1, 4)
        selected_products = random.sample(products, num_items)
        
        total = 0.0
        for product in selected_products:
            quantity = random.randint(1, 2)
            # Price might have changed, so store historical price
            price_at_purchase = product.price * random.uniform(0.9, 1.1)  # ±10% variation
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price_at_purchase=round(price_at_purchase, 2)
            )
            db.add(order_item)
            order_items_list.append(order_item)
            
            total += price_at_purchase * quantity
        
        order.total_amount = round(total, 2)
        orders.append(order)
    
    db.flush()
    logger.info(f"Seeded {len(orders)} orders with {len(order_items_list)} order items")
    return orders


def seed_database():
    """Main seeding function"""
    logger.info("Starting database seeding...")
    
    # Initialize database
    init_db()
    
    with get_db_session() as db:
        # Check if already seeded
        existing_customers = db.query(Customer).count()
        if existing_customers > 0:
            logger.info(f"Database already seeded ({existing_customers} customers found). Skipping.")
            return
        
        # Seed data
        customers = seed_customers(db)
        products = seed_products(db)
        orders = seed_orders(db, customers, products)
        
        logger.info("Database seeding completed successfully!")
        logger.info(f"Summary: {len(customers)} customers, {len(products)} products, {len(orders)} orders")


if __name__ == "__main__":
    seed_database()
