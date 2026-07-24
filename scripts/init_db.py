#!/usr/bin/env python3
"""
Database initialization script for AICF v2.

This script runs Alembic migrations to create all database tables.
Usage: python scripts/init_db.py
"""

import os
import sys

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command


def init_database():
    """Initialize the database by running Alembic migrations."""
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Path to alembic.ini
    alembic_ini_path = os.path.join(project_root, 'alembic.ini')
    
    if not os.path.exists(alembic_ini_path):
        print(f"ERROR: alembic.ini not found at {alembic_ini_path}")
        sys.exit(1)
    
    # Create Alembic config
    alembic_cfg = Config(alembic_ini_path)
    
    # Set working directory to project root for relative paths
    os.chdir(project_root)
    
    print("Initializing AICF database...")
    print(f"Using configuration: {alembic_ini_path}")
    
    try:
        # Run upgrade to head
        command.upgrade(alembic_cfg, "head")
        print("\n✓ Database initialized successfully!")
        print("All tables have been created.")
    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
