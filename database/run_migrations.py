import os
import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import engine

def run_migrations():
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        print("No migrations folder found.")
        return

    # Find and sort all SQL files in the migrations directory
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        print("No migration SQL files found.")
        return

    print(f"Found {len(sql_files)} migration files in {migrations_dir}")

    with engine.connect() as conn:
        for sql_file in sql_files:
            print(f"Running migration: {sql_file.name}...", end="", flush=True)
            try:
                # Read the file content
                sql_content = sql_file.read_text(encoding="utf-8")
                
                # SQLAlchemy requires raw SQL to be executed via text() inside a transaction
                # Split commands if necessary or run the batch
                if sql_content.strip():
                    conn.execute(text(sql_content))
                
                print(" OK")
            except Exception as e:
                print(" FAILED")
                print(f"Error executing {sql_file.name}: {e}")
                # Optional: break or rollback depending on user preference.
                # We will continue or raise to let the user know.
                print("Continuing with next migration...")

        # Explicitly commit changes
        conn.commit()
    print("Database migrations complete!")

if __name__ == "__main__":
    run_migrations()
