"""
Standalone script to migrate data from SQLite to Neon Postgres.

Usage:
    python migrate_to_neon.py

Make sure to set DATABASE_URL environment variable before running.
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
    with open(env_file, "r", encoding="utf-8") as f:
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
import django  # noqa: E402

django.setup()

import subprocess  # noqa: E402

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402


def main():
    print("=" * 60)
    print("SQLite to Neon Postgres Migration")
    print("=" * 60)

    # Check if DATABASE_URL is set
    database_url = os.environ.get("SUPABASE_URL")
    if not database_url:
        print(
            "\n[ERROR] SUPABASE_URL environment variable is not set!\n"
            "Please set it in your .env file or environment variables:\n"
            "  postgresql://user:password@host:port/dbname?sslmode=require\n"
        )
        return False

    # Get SQLite database path
    sqlite_path = None

    # Try to find SQLite file
    possible_paths = [
        BASE_DIR / "db.sqlite3",
        BASE_DIR.parent / "db.sqlite3",
        Path(settings.BASE_DIR) / "db.sqlite3",
    ]

    for path in possible_paths:
        if path.exists():
            sqlite_path = path
            break

    if not sqlite_path:
        print(
            "\n[ERROR] SQLite database not found.\n"
            "Searched in:\n"
            + "\n".join(f"  - {p}" for p in possible_paths)
        )
        return False

    print(f"\n[OK] SQLite database found: {sqlite_path}")

    # Check if running in CI/CD (non-interactive mode)
    ci_mode = os.environ.get("CI", "false").lower() == "true"
    auto_confirm = os.environ.get("AUTO_CONFIRM_MIGRATION", "false").lower() == "true"

    # Confirm migration (skip in CI/CD or if AUTO_CONFIRM_MIGRATION is set)
    if not (ci_mode or auto_confirm):
        confirm = input(
            "\nThis will:\n"
            "1. Export all data from SQLite\n"
            "2. Run migrations on Supabase Postgres\n"
            "3. Import all data into Supabase Postgres\n\n"
            "Continue? (yes/no): "
        )
        if confirm.lower() not in ["yes", "y"]:
            print("Migration cancelled.")
            return False
    else:
        print("\n[INFO] Running in non-interactive mode (CI/CD)")
        print("This will:\n"
              "1. Export all data from SQLite\n"
              "2. Run migrations on Neon Postgres\n"
              "3. Import all data into Neon Postgres\n")

    # Step 1: Export data from SQLite
    print("\n" + "=" * 60)
    print("Step 1: Exporting data from SQLite...")
    print("=" * 60)

    export_file = BASE_DIR / "sqlite_export.json"

    try:
        print("Exporting all data...")
        # Temporarily unset DATABASE_URL to force SQLite usage
        env = os.environ.copy()
        if "DATABASE_URL" in env:
            del env["DATABASE_URL"]

        # Run dumpdata in a subprocess with DATABASE_URL unset
        # This ensures it uses SQLite from the base settings
        result = subprocess.run(
            [
                sys.executable,
                "manage.py",
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
            ],
            env=env,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            raise Exception(f"dumpdata failed: {result.stderr}")

        # Write the output to file
        with open(export_file, "w", encoding="utf-8") as f:
            f.write(result.stdout)

        file_size = export_file.stat().st_size
        print(f"[OK] Data exported to {export_file} ({file_size:,} bytes)")
    except Exception as e:
        print(f"[ERROR] Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 2: Setup Neon Postgres
    print("\n" + "=" * 60)
    print("Step 2: Setting up Neon Postgres database...")
    print("=" * 60)

    # Ensure we're using the original config (with DATABASE_URL)
    connections.close_all()

    try:
        # Test connection
        db = connections["default"]
        db.ensure_connection()
        print("[OK] Connected to Neon Postgres")

        # Run migrations
        print("Running migrations...")
        call_command("migrate", "--noinput")
        print("[OK] Migrations completed")
    except Exception as e:
        print(f"[ERROR] Failed to setup Postgres: {e}")
        return False

    # Step 3: Import data into Neon
    print("\n" + "=" * 60)
    print("Step 3: Importing data into Neon Postgres...")
    print("=" * 60)

    try:
        print("Loading data...")
        call_command("loaddata", str(export_file), verbosity=0)
        print("[OK] Data imported successfully!")
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        print(
            "\nYou may need to manually fix conflicts.\n"
            f"Try running: python manage.py loaddata {export_file}"
        )
        return False

    # Cleanup
    print("\n" + "=" * 60)
    print("Cleaning up...")
    print("=" * 60)

    try:
        if export_file.exists():
            # In CI/CD, always remove the export file
            if ci_mode or auto_confirm:
                export_file.unlink()
                print(f"[OK] Removed {export_file} (CI/CD mode)")
            else:
                keep = (
                    input(f"\nDelete export file {export_file}? (yes/no) [no]: ").lower()
                    not in ["yes", "y"]
                )
                if not keep:
                    export_file.unlink()
                    print(f"[OK] Removed {export_file}")
    except Exception as e:
        print(f"[WARNING] Cleanup warning: {e}")

    print("\n" + "=" * 60)
    print("[OK] Migration completed successfully!")
    print("=" * 60)
    print(
        "\nYour application is now using Neon Postgres.\n"
        "Make sure SUPABASE_URL is set in your production environment.\n"
    )
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
