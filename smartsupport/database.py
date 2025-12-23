from datetime import datetime
from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = "sqlite:///./smartsupport.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OrderStatus(enum.Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    orders = relationship("Order", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}')>"


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    order_items = relationship("OrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price=${self.price})>"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_amount = Column(Float, nullable=False)
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.id}, customer_id={self.customer_id}, status={self.status.value}, total=${self.total_amount})>"


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    logger.info("Database initialized successfully")
