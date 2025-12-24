"""
Test script to verify Neon database connection.

This script will:
1. Load DATABASE_URL from .env file (if exists)
2. Test the connection to Neon Postgres
3. Display connection information
"""
import os
import sys
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Try to load .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    print("Loading .env file...")
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                os.environ[key.strip()] = value
    print("[OK] .env file loaded\n")

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "studevPH.settings.dev")

try:
    import django

    django.setup()
except ImportError:
    print("[ERROR] Django is not installed. Please install dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

from django.db import connection
from django.conf import settings


def test_connection():
    print("=" * 60)
    print("Neon Database Connection Test")
    print("=" * 60)

    # Check if DATABASE_URL is set
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("\n[ERROR] DATABASE_URL environment variable is not set!")
        print("Please set it in your .env file or environment variables.")
        return False

    # Mask password in URL for display
    if "@" in database_url and "://" in database_url:
        parts = database_url.split("@")
        if len(parts) == 2:
            protocol_user_pass = parts[0]
            if ":" in protocol_user_pass.split("://")[1]:
                protocol, user_pass = protocol_user_pass.split("://")
                user, _ = user_pass.split(":", 1)
                masked_url = f"{protocol}://{user}:***@{parts[1]}"
                print(f"\nDATABASE_URL: {masked_url}")
            else:
                print(f"\nDATABASE_URL: [set]")
        else:
            print(f"\nDATABASE_URL: [set]")
    else:
        print(f"\nDATABASE_URL: [set]")

    # Display database configuration
    db_config = settings.DATABASES["default"]
    engine = db_config.get("ENGINE", "unknown")

    print("\n" + "-" * 60)
    print("Database Configuration:")
    print("-" * 60)

    if "postgresql" in engine or "postgres" in engine:
        db_type = "PostgreSQL (Neon)"
        host = db_config.get("HOST", "N/A")
        port = db_config.get("PORT", "N/A")
        name = db_config.get("NAME", "N/A")
        user = db_config.get("USER", "N/A")

        print(f"Type: {db_type}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Database: {name}")
        print(f"User: {user}")
    elif "sqlite" in engine:
        print(f"Type: SQLite")
        print(f"Database: {db_config.get('NAME', 'N/A')}")
        print("\n[WARNING] Currently using SQLite, not Neon Postgres!")
        print("Make sure DATABASE_URL is set correctly.")
        return False
    else:
        print(f"Type: {engine}")

    # Test connection
    print("\n" + "-" * 60)
    print("Testing Connection...")
    print("-" * 60)

    try:
        # Ensure connection
        db = connections["default"]
        db.ensure_connection()
        print("[OK] Connection established successfully!")

        # Get database version
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"\n[OK] Database Version:")
            print(f"  {version}")

            # Test a simple query
            cursor.execute("SELECT 1 as test_value, current_database() as db_name, current_user as db_user;")
            result = cursor.fetchone()
            if result:
                print(f"\n[OK] Query test passed!")
                print(f"  Test Value: {result[0]}")
                print(f"  Database Name: {result[1]}")
                print(f"  Database User: {result[2]}")

            # Get some database info
            cursor.execute("SELECT current_database(), version();")
            db_info = cursor.fetchone()
            print(f"\n[OK] Connection Details:")
            print(f"  Connected to: {db_info[0]}")
            print(f"  PostgreSQL Version: {db_info[1].split(',')[0]}")

        print("\n" + "=" * 60)
        print("[OK] Connection test completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] Connection failed!")
        print(f"  Error: {str(e)}")
        print("\n" + "-" * 60)
        print("Troubleshooting:")
        print("-" * 60)
        print("1. Check if DATABASE_URL is correct")
        print("2. Verify your Neon database is running")
        print("3. Check network connectivity")
        print("4. Ensure SSL is properly configured")
        print("5. Verify credentials are correct")
        return False


if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

