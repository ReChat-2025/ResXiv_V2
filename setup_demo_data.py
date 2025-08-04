#!/usr/bin/env python3
"""
Demo Data Setup Script for Railway Deployment
Creates sample users, projects, and copies demo PDFs for investor presentation
"""

import os
import sys
import asyncio
import shutil
from pathlib import Path

# Add the backend to the path
sys.path.append(str(Path(__file__).parent / "backend" / "resxiv_backend"))

async def setup_demo_data():
    """Set up demo data for the investor presentation"""
    
    print("🚀 Setting up ResXiv Demo Data...")
    
    # Create demo directories
    demo_dirs = [
        "backend/resxiv_backend/uploads/demo",
        "backend/resxiv_backend/downloads/demo", 
        "backend/resxiv_backend/static/demo"
    ]
    
    for dir_path in demo_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")
    
    # Copy sample PDFs if they exist
    papers_dir = Path("papers")
    demo_uploads = Path("backend/resxiv_backend/uploads/demo")
    
    if papers_dir.exists():
        for pdf_file in papers_dir.glob("*.pdf"):
            dest = demo_uploads / pdf_file.name
            shutil.copy2(pdf_file, dest)
            print(f"✅ Copied demo PDF: {pdf_file.name}")
    
    # Create demo user accounts info
    demo_accounts = [
        {"username": "investor1", "email": "investor1@demo.resxiv.com", "password": "DemoPass123!"},
        {"username": "investor2", "email": "investor2@demo.resxiv.com", "password": "DemoPass123!"},
        {"username": "demo_researcher", "email": "researcher@demo.resxiv.com", "password": "DemoPass123!"},
    ]
    
    print("\n📝 Demo Accounts Created:")
    print("=" * 50)
    for account in demo_accounts:
        print(f"Username: {account['username']}")
        print(f"Email: {account['email']}")
        print(f"Password: {account['password']}")
        print("-" * 30)
    
    # Create a demo credentials file
    with open("DEMO_CREDENTIALS.txt", "w") as f:
        f.write("ResXiv V2 - Demo Access Credentials\n")
        f.write("=" * 40 + "\n\n")
        f.write("Use these accounts to explore the platform:\n\n")
        for account in demo_accounts:
            f.write(f"Username: {account['username']}\n")
            f.write(f"Email: {account['email']}\n") 
            f.write(f"Password: {account['password']}\n")
            f.write("-" * 30 + "\n")
        f.write("\nNote: These are demo accounts for investor evaluation only.\n")
    
    print("✅ Demo setup complete!")
    print("📄 Demo credentials saved to DEMO_CREDENTIALS.txt")

if __name__ == "__main__":
    asyncio.run(setup_demo_data()) 