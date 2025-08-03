"""
Database configuration for ResXiv setup
Modify these values according to your local setup
"""

# PostgreSQL Configuration
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres', 
    'password': 'postgres',  # Change this to your actual password
    'database': 'resxiv'
}

# MongoDB Configuration  
MONGODB_CONFIG = {
    'host': 'localhost',
    'port': 27017,
    'database': 'resxiv_chat',
    'username': None,  # Set if MongoDB requires auth
    'password': None   # Set if MongoDB requires auth
} 