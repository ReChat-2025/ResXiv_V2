#!/usr/bin/env python3
"""
Simple script to create the ResXiv PostgreSQL database
Run this first if you're having database creation issues
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    # Default configuration
    config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',  # Change this to your actual password
        'database': 'postgres'  # Connect to default database first
    }
    
    target_db = 'resxiv'
    
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"Connected to PostgreSQL server at {config['host']}:{config['port']}")
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'")
        exists = cursor.fetchone() is not None
        
        if exists:
            print(f"Database '{target_db}' already exists")
        else:
            # Create database
            cursor.execute(f"CREATE DATABASE {target_db}")
            print(f"Created database '{target_db}'")
        
        # Test connection to the new database
        cursor.close()
        conn.close()
        
        # Connect to the target database
        config['database'] = target_db
        test_conn = psycopg2.connect(**config)
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT version()")
        version = test_cursor.fetchone()[0]
        print(f"Successfully connected to '{target_db}' database")
        print(f"PostgreSQL version: {version}")
        
        test_cursor.close()
        test_conn.close()
        
        print("✅ Database creation successful!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your PostgreSQL username/password")
        print("3. Verify PostgreSQL is accepting connections on localhost:5432")
        print("4. Try: sudo -u postgres psql -c 'CREATE DATABASE ResXiv;'")

if __name__ == "__main__":
    create_database() 