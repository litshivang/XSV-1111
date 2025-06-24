import sys
import logging
from app.database import init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    try:
        logger.info("Initializing database and creating tables...")
        init_db()
        logger.info("Database setup completed successfully.")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
