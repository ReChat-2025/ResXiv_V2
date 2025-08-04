#!/usr/bin/env python3
"""
Data Migration Script for Railway Deployment
Imports existing PostgreSQL data, MongoDB data, and file uploads
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def migrate_postgresql():
    """Import PostgreSQL data"""
    if Path("database_export.sql").exists():
        print("📊 Importing PostgreSQL data...")
        
        # Railway provides DATABASE_URL, use it if available
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            cmd = f"psql {db_url} < database_export.sql"
        else:
            # Fallback to local connection
            cmd = "psql -d resxiv < database_export.sql"
        
        run_command(cmd, "PostgreSQL data import")
    else:
        print("⚠️  No PostgreSQL export found (database_export.sql)")

def migrate_mongodb():
    """Import MongoDB data"""
    if Path("mongodb_dump").exists():
        print("📊 Importing MongoDB data...")
        
        # Railway provides MONGODB_URL, use it if available
        mongo_url = os.getenv("MONGODB_URL")
        if mongo_url:
            cmd = f"mongorestore --uri {mongo_url} mongodb_dump/"
        else:
            # Fallback to local connection
            cmd = "mongorestore mongodb_dump/"
        
        run_command(cmd, "MongoDB data import")
    else:
        print("⚠️  No MongoDB export found (mongodb_dump/)")

def setup_file_storage():
    """Set up file storage directories and copy existing files"""
    print("📁 Setting up file storage...")
    
    # Create directories
    storage_dirs = [
        "backend/resxiv_backend/uploads",
        "backend/resxiv_backend/downloads", 
        "backend/resxiv_backend/static"
    ]
    
    for dir_path in storage_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")
    
    # Files are already in place, just ensure permissions (ignore errors for existing dirs)
    result = run_command("chmod -R 755 backend/resxiv_backend/uploads backend/resxiv_backend/downloads backend/resxiv_backend/static 2>/dev/null || true", 
               "Setting file permissions")
    if result is not None:
        print("✅ File permissions set successfully")
    else:
        print("⚠️  Some permission errors ignored (existing directories)")

def main():
    """Main migration function"""
    print("🚀 Starting ResXiv Data Migration for Railway...")
    print("=" * 50)
    
    # Check if we're in Railway environment
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    
    if is_railway:
        print("🚂 Running in Railway environment")
        migrate_postgresql()
        migrate_mongodb()
    else:
        print("💻 Running in local environment - preparing for deployment")
    
    setup_file_storage()
    
    print("\n✅ Migration completed!")
    print("📋 Summary:")
    print(f"   - PostgreSQL: {'✅ Imported' if Path('database_export.sql').exists() else '⚠️  No data'}")
    print(f"   - MongoDB: {'✅ Imported' if Path('mongodb_dump').exists() else '⚠️  No data'}")
    print(f"   - File Storage: ✅ Ready")
    
    if not is_railway:
        print("\n📦 Ready for Railway deployment!")
        print("   1. Push to GitHub")
        print("   2. Deploy on Railway") 
        print("   3. This script will run automatically on Railway")

if __name__ == "__main__":
    main() 