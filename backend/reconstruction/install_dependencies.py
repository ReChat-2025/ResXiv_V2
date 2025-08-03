#!/usr/bin/env python3
"""
ResXiv PostgreSQL Dependencies Installer
This script ensures all required PostgreSQL extensions are installed.
"""

import subprocess
import sys
import logging
import argparse
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DependencyInstaller:
    def __init__(self):
        self.postgres_version = self._get_postgres_version()
        logger.info(f"Detected PostgreSQL version: {self.postgres_version}")
    
    def _get_postgres_version(self):
        """Get the installed PostgreSQL version"""
        try:
            result = subprocess.run(['sudo', '-u', 'postgres', 'psql', '--version'], 
                                  capture_output=True, text=True, check=True)
            version_line = result.stdout.strip()
            # Extract version number (e.g., "psql (PostgreSQL) 16.1" -> "16")
            version = version_line.split('(PostgreSQL)')[1].strip().split('.')[0]
            return version
        except Exception as e:
            logger.warning(f"Could not detect PostgreSQL version: {e}")
            return "16"  # Default to 16
    
    def _run_command(self, command, description):
        """Run a system command and handle errors"""
        try:
            logger.info(f"Running: {description}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            logger.info(f"✅ {description} - Success")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ {description} - Failed: {e.stderr}")
            return False
    
    def update_package_lists(self):
        """Update package lists"""
        return self._run_command("sudo apt update", "Updating package lists")
    
    def install_postgresql_contrib(self):
        """Install PostgreSQL contrib package for pgcrypto"""
        # Try different package naming conventions
        packages = [
            f"postgresql-{self.postgres_version}-contrib",
            f"postgresql-contrib-{self.postgres_version}",
            "postgresql-contrib"
        ]
        
        for package in packages:
            if self._run_command(f"sudo apt install -y {package}", f"Installing {package}"):
                return True
        
        logger.error("Could not install PostgreSQL contrib package")
        return False
    
    def install_pgvector(self):
        """Install pgvector extension"""
        # First fix any broken packages
        self._run_command("sudo apt --fix-broken install -y", "Fixing broken packages")
        
        # Try to install pgvector package first
        pgvector_packages = [
            f"postgresql-{self.postgres_version}-pgvector",
            "postgresql-pgvector"
        ]
        
        for package in pgvector_packages:
            if self._run_command(f"sudo apt install -y {package}", f"Installing {package}"):
                return True
        
        # If package fails, try building from source
        logger.info("Package installation failed, trying to build pgvector from source...")
        
        # Install build dependencies
        build_deps = [
            "sudo apt install -y build-essential git",
            "sudo apt install -y postgresql-server-dev-all"
        ]
        
        for cmd in build_deps:
            self._run_command(cmd, f"Installing build dependencies")
        
        return self._build_pgvector_from_source()
    
    def _build_pgvector_from_source(self):
        """Build pgvector from source as fallback"""
        commands = [
            ("cd /tmp && git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git", 
             "Cloning pgvector repository"),
            ("cd /tmp/pgvector && make", "Building pgvector"),
            ("cd /tmp/pgvector && sudo make install", "Installing pgvector"),
            ("rm -rf /tmp/pgvector", "Cleaning up build files")
        ]
        
        for command, description in commands:
            if not self._run_command(command, description):
                return False
        
        return True
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        return self._run_command(
            "pip install psycopg2-binary pymongo python-dotenv",
            "Installing Python dependencies"
        )
    
    def verify_extensions(self):
        """Verify that extensions can be created in PostgreSQL"""
        try:
            # Test pgcrypto
            result = subprocess.run([
                'sudo', '-u', 'postgres', 'psql', '-d', 'postgres', 
                '-c', 'CREATE EXTENSION IF NOT EXISTS pgcrypto; DROP EXTENSION IF EXISTS pgcrypto;'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ pgcrypto extension verified")
            else:
                logger.error("❌ pgcrypto extension failed")
                return False
            
            # Test pgvector
            result = subprocess.run([
                'sudo', '-u', 'postgres', 'psql', '-d', 'postgres', 
                '-c', 'CREATE EXTENSION IF NOT EXISTS vector; DROP EXTENSION IF EXISTS vector;'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ pgvector extension verified")
            else:
                logger.warning("⚠️  pgvector extension not available (vector search will be disabled)")
            
            return True
            
        except Exception as e:
            logger.error(f"Extension verification failed: {e}")
            return False
    
    def restart_postgresql(self):
        """Restart PostgreSQL service"""
        return self._run_command("sudo systemctl restart postgresql", "Restarting PostgreSQL")
    
    def run_full_installation(self):
        """Run the complete installation process"""
        logger.info("Starting ResXiv dependency installation...")
        
        # Fix any package issues first
        self._run_command("sudo apt --fix-broken install -y", "Fixing any broken packages")
        
        steps = [
            ("Update package lists", self.update_package_lists),
            ("Install Python dependencies", self.install_python_dependencies),
            ("Install PostgreSQL contrib", self.install_postgresql_contrib),
            ("Install pgvector", self.install_pgvector),
            ("Restart PostgreSQL", self.restart_postgresql),
            ("Verify extensions", self.verify_extensions)
        ]
        
        critical_steps = ["Install PostgreSQL contrib", "Install Python dependencies"]
        failed_steps = []
        
        for step_name, step_func in steps:
            logger.info(f"\n--- {step_name} ---")
            if not step_func():
                failed_steps.append(step_name)
                if step_name in critical_steps:
                    logger.error(f"Critical step failed: {step_name}")
                else:
                    logger.warning(f"Optional step failed: {step_name}")
            else:
                logger.info(f"Step completed: {step_name}")
        
        critical_failures = [step for step in failed_steps if step in critical_steps]
        
        if critical_failures:
            logger.error(f"\n❌ Critical installation failures: {', '.join(critical_failures)}")
            return False
        elif failed_steps:
            logger.warning(f"\n⚠️  Installation completed with optional failures: {', '.join(failed_steps)}")
            logger.info("The database setup will work with reduced functionality (no vector search).")
            logger.info("You can now run: python setup_databases.py")
            return True
        else:
            logger.info("\n✅ All dependencies installed successfully!")
            logger.info("You can now run: python setup_databases.py")
            return True

def main():
    parser = argparse.ArgumentParser(description='Install ResXiv PostgreSQL dependencies')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Only verify existing installations')
    
    args = parser.parse_args()
    
    installer = DependencyInstaller()
    
    if args.verify_only:
        success = installer.verify_extensions()
        sys.exit(0 if success else 1)
    else:
        success = installer.run_full_installation()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 