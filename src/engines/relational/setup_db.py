"""
Database setup and migration utility for TriQuery.
Executes schema.sql and seed_data.sql against MySQL 8.x (or isolated SQLite test store).
Can be run standalone: python -m src.engines.relational.setup_db
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.config import DatabaseConfig, config
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine

console = Console()


def setup_database(db_config: DatabaseConfig) -> bool:
    """Executes schema creation and seed data insertion."""
    console.print(f"\n[bold cyan]TriQuery Database Setup[/bold cyan]")
    console.print(f"Target: [bold]{'SQLite Isolated Mode' if db_config.sqlite_fallback or db_config.driver == 'sqlite' else f'MySQL 8.x ({db_config.host}:{db_config.port}/{db_config.name})'}[/bold]")

    conn_mgr = DatabaseConnectionManager(db_config)
    engine = RelationalEngine(conn_mgr)

    # 1. Health / Reachability Check
    healthy, msg = conn_mgr.test_connection()
    if not healthy:
        console.print(f"[bold red][ERROR] Database Connection Failed:[/bold red] {msg}")
        return False
    console.print(f"[green][OK] Connection verified:[/green] {msg}")

    # 2. Execute Schema
    schema_file = config.database_dir / "schema.sql"
    console.print(f"Executing schema from: [blue]{schema_file}[/blue]...")
    try:
        engine.execute_script_file(schema_file)
        console.print("[green][OK] Schema executed successfully.[/green]")
    except Exception as exc:
        console.print(f"[bold red][ERROR] Failed to execute schema:[/bold red] {exc}")
        return False

    # 3. Execute Seed Data
    seed_file = config.database_dir / "seed_data.sql"
    console.print(f"Executing seed data from: [blue]{seed_file}[/blue]...")
    try:
        engine.execute_script_file(seed_file)
        console.print("[green][OK] Seed data loaded successfully.[/green]")
    except Exception as exc:
        console.print(f"[bold red][ERROR] Failed to execute seed data:[/bold red] {exc}")
        return False

    # 4. Display Table Counts
    counts = engine.get_table_counts()
    table = Table(title="TriQuery Relational Storage Verification")
    table.add_column("Table Name", style="cyan", justify="left")
    table.add_column("Row Count", style="green", justify="right")

    for tbl_name, row_count in counts.items():
        table.add_row(tbl_name, str(row_count))

    console.print(table)
    console.print("[bold green][SUCCESS] Relational database setup completed successfully![/bold green]\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="TriQuery Relational Database Setup")
    parser.add_argument(
        "--driver",
        choices=["mysql", "sqlite"],
        default=None,
        help="Target database backend (default: read from .env)"
    )
    args = parser.parse_args()

    if args.driver:
        custom_cfg = DatabaseConfig(
            driver=args.driver,
            sqlite_fallback=(args.driver == "sqlite")
        )
    else:
        custom_cfg = config.db

    success = setup_database(custom_cfg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
