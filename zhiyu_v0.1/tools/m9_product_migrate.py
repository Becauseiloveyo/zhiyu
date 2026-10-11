"""Explicitly install isolated, versioned demo metadata in the configured PostgreSQL database."""
from zhiyu.db.session import get_engine
from zhiyu.product.demo_store import initialize

if __name__ == "__main__":
    initialize(get_engine())
    print("Product demo schema 0001 ready; core schema and security facts unchanged.")
