import os
import sys
import time
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.core.config import settings


def create_database():
    """Create the database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (settings.POSTGRES_DB,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database {settings.POSTGRES_DB}...")
            cursor.execute(f'CREATE DATABASE {settings.POSTGRES_DB}')
            print("Database created successfully!")
        else:
            print(f"Database {settings.POSTGRES_DB} already exists.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)


def check_db_connection():
    """Check if the database connection is working."""
    try:
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful!")
        return True
    except SQLAlchemyError as e:
        print(f"Error connecting to database: {e}")
        return False


def run_migrations():
    """Run database migrations."""
    try:
        print("Running database migrations...")
        os.system("alembic upgrade head")
        print("Migrations completed successfully!")
    except Exception as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)


def main():
    """Main initialization function."""
    print("Starting database initialization...")
    
    # Create database
    create_database()
    
    # Run migrations
    run_migrations()
    
    # Check connection
    if check_db_connection():
        print("\nDatabase initialization completed successfully!")
    else:
        print("\nDatabase initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 