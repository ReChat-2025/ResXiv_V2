#!/usr/bin/env python3
"""
Database Migration Runner

CLI script to run database migrations for the ResXiv backend.
This script properly fixes the project slug uniqueness constraint to work with soft deletes.

Usage:
    python run_migration.py                                    # Check migration status and run if needed
    python run_migration.py --run                              # Force run migration
    python run_migration.py --rollback                         # Rollback migration
    python run_migration.py --list                             # List all migrations
    python run_migration.py --check                            # Check if migration is needed
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database.migrations import migration_manager, run_project_slug_fix, check_migration_needed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Database Migration Runner for ResXiv Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_migration.py                    # Check and run migration if needed
  python run_migration.py --run              # Force run the migration
  python run_migration.py --rollback         # Rollback the migration
  python run_migration.py --list             # List all available migrations
  python run_migration.py --check            # Check if migration is needed
        """
    )
    
    parser.add_argument(
        "--run",
        action="store_true",
        help="Force run the project slug fix migration"
    )
    
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the project slug fix migration"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available migrations"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if migration is needed without running it"
    )
    
    parser.add_argument(
        "--migration-id",
        default="001_fix_project_slug_uniqueness",
        help="Specific migration ID to run (default: %(default)s)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.list:
            await list_migrations()
        elif args.check:
            await check_migration_status()
        elif args.rollback:
            await rollback_migration(args.migration_id)
        elif args.run:
            await run_migration(args.migration_id)
        else:
            # Default behavior: check if needed and run if so
            await auto_migrate()
            
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed with error: {str(e)}")
        sys.exit(1)


async def list_migrations():
    """List all available migrations"""
    print("\n📋 Available Migrations:")
    print("=" * 50)
    
    migrations = await migration_manager.list_migrations()
    for migration in migrations:
        print(f"ID: {migration['id']}")
        print(f"Description: {migration['description']}")
        print(f"Version: {migration['version']}")
        print("-" * 30)


async def check_migration_status():
    """Check if migration is needed"""
    print("\n🔍 Checking Migration Status...")
    print("=" * 40)
    
    is_needed = await check_migration_needed()
    if is_needed:
        print("✅ Migration IS NEEDED")
        print("   The project slug uniqueness constraint needs to be fixed.")
        print("   Run with --run to apply the migration.")
    else:
        print("✅ Migration NOT NEEDED")
        print("   The project slug uniqueness constraint is already properly configured.")


async def run_migration(migration_id: str):
    """Run a specific migration"""
    print(f"\n🚀 Running Migration: {migration_id}")
    print("=" * 50)
    
    success = await migration_manager.run_migration(migration_id)
    if success:
        print("✅ Migration completed successfully!")
        print("\n🎉 Benefits of this fix:")
        print("   • You can now reuse project names after deleting projects")
        print("   • Soft-deleted projects no longer block new projects with same name")
        print("   • Maintains data integrity for active projects")
        print("   • Follows industry best practices for soft-delete uniqueness")
    else:
        print("❌ Migration failed!")
        print("   Check the logs above for details.")
        sys.exit(1)


async def rollback_migration(migration_id: str):
    """Rollback a specific migration"""
    print(f"\n⚠️  Rolling Back Migration: {migration_id}")
    print("=" * 50)
    
    # Warn user about potential issues
    print("WARNING: Rolling back may fail if there are duplicate slugs in soft-deleted projects.")
    response = input("Are you sure you want to continue? (y/N): ")
    if response.lower() != 'y':
        print("Rollback cancelled.")
        return
    
    success = await migration_manager.rollback_migration(migration_id)
    if success:
        print("✅ Migration rollback completed successfully!")
    else:
        print("❌ Migration rollback failed!")
        sys.exit(1)


async def auto_migrate():
    """Check if migration is needed and run if so"""
    print("\n🔍 Auto-Migration Check")
    print("=" * 30)
    
    is_needed = await check_migration_needed()
    if is_needed:
        print("Migration needed. Running automatically...")
        await run_migration("001_fix_project_slug_uniqueness")
    else:
        print("✅ No migration needed. Database is up to date.")


if __name__ == "__main__":
    print("🔧 ResXiv Database Migration Runner")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Error: This script must be run from the resxiv_backend directory")
        print("   Current directory should contain the 'app' folder")
        sys.exit(1)
    
    asyncio.run(main()) 