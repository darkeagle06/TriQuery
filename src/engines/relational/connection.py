"""
Database connection manager for TriQuery Relational Engine.
Supports MySQL 8.x via PyMySQL / mysql-connector-python with connection health checking,
and provides an in-memory/file SQLite fallback for isolated unit testing.
Never hardcodes credentials; all parameters originate from environment configuration.
"""

import contextlib
import logging
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from src.config import DatabaseConfig, config

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Manages database connections, connection pooling, and lifecycle.
    Separates database connectivity details from query execution logic.
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        self.cfg = db_config or config.db
        self._sqlite_conn: Optional[sqlite3.Connection] = None

        # Determine mode explicitly
        self._is_sqlite_mode: bool = (
            self.cfg.sqlite_fallback or self.cfg.driver.lower() == "sqlite"
        )

    @property
    def is_sqlite_mode(self) -> bool:
        return self._is_sqlite_mode

    def ensure_database_exists(self) -> bool:
        """
        Safely creates the database if it doesn't already exist on MySQL server.
        Never drops or overwrites any existing database or data.
        """
        if self._is_sqlite_mode:
            return True

        try:
            import pymysql
            conn = pymysql.connect(
                host=self.cfg.host,
                port=self.cfg.port,
                user=self.cfg.user,
                password=self.cfg.password,
                charset=self.cfg.charset,
                autocommit=True,
                connect_timeout=3,
            )
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.cfg.name}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
            conn.close()
            return True
        except ImportError:
            try:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=self.cfg.host,
                    port=self.cfg.port,
                    user=self.cfg.user,
                    password=self.cfg.password,
                    charset=self.cfg.charset,
                    autocommit=True,
                    connection_timeout=3,
                )
                cursor = conn.cursor()
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.cfg.name}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
                cursor.close()
                conn.close()
                return True
            except Exception:
                return False
        except Exception:
            return False

    def get_connection(self):
        """
        Returns an active database connection.
        If in SQLite mode, returns the persistent SQLite connection.
        If in MySQL mode, creates a connection via PyMySQL or mysql.connector.
        """
        if self._is_sqlite_mode:
            return self._get_sqlite_connection()

        # Try PyMySQL first (pure Python, Python 3.13 compatible)
        try:
            import pymysql
            from pymysql.constants import CLIENT
            from pymysql.cursors import DictCursor

            try:
                conn = pymysql.connect(
                    host=self.cfg.host,
                    port=self.cfg.port,
                    user=self.cfg.user,
                    password=self.cfg.password,
                    database=self.cfg.name,
                    charset=self.cfg.charset,
                    cursorclass=DictCursor,
                    autocommit=True,
                    connect_timeout=3,
                    client_flag=CLIENT.MULTI_STATEMENTS,
                )
                return conn
            except pymysql.err.OperationalError as op_err:
                # Error 1049: Unknown database -> safely create database and retry
                if op_err.args and op_err.args[0] == 1049:
                    self.ensure_database_exists()
                    conn = pymysql.connect(
                        host=self.cfg.host,
                        port=self.cfg.port,
                        user=self.cfg.user,
                        password=self.cfg.password,
                        database=self.cfg.name,
                        charset=self.cfg.charset,
                        cursorclass=DictCursor,
                        autocommit=True,
                        connect_timeout=3,
                        client_flag=CLIENT.MULTI_STATEMENTS,
                    )
                    return conn
                raise
        except ImportError:
            pass

        # Try official mysql.connector as alternative
        try:
            import mysql.connector

            try:
                conn = mysql.connector.connect(
                    host=self.cfg.host,
                    port=self.cfg.port,
                    user=self.cfg.user,
                    password=self.cfg.password,
                    database=self.cfg.name,
                    charset=self.cfg.charset,
                    autocommit=True,
                    connection_timeout=3,
                )
                return conn
            except mysql.connector.Error as db_err:
                if getattr(db_err, "errno", None) == 1049:
                    self.ensure_database_exists()
                    conn = mysql.connector.connect(
                        host=self.cfg.host,
                        port=self.cfg.port,
                        user=self.cfg.user,
                        password=self.cfg.password,
                        database=self.cfg.name,
                        charset=self.cfg.charset,
                        autocommit=True,
                        connection_timeout=3,
                    )
                    return conn
                raise
        except ImportError:
            pass

        # If neither driver is installed:
        if self.cfg.sqlite_fallback:
            logger.info("No MySQL driver found; falling back to SQLite test connection as requested.")
            self._is_sqlite_mode = True
            return self._get_sqlite_connection()

        raise ModuleNotFoundError(
            "No MySQL driver installed. To connect to MySQL 8.x, install 'pymysql' via: \n"
            "    pip install pymysql\n"
            "Alternatively, set DB_DRIVER=sqlite or DB_TEST_SQLITE_FALLBACK=true in .env for isolated standalone mode."
        )

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        """Maintains a persistent SQLite database connection for tests and standalone mode."""
        from pathlib import Path
        if self._sqlite_conn is None:
            if self.cfg.sqlite_path == ":memory:":
                target_path = ":memory:"
                needs_init = False
            elif self.cfg.sqlite_path:
                target_path = str(self.cfg.sqlite_path)
                needs_init = not Path(target_path).exists()
            else:
                db_file = config.database_dir / "triquery_local.db"
                target_path = str(db_file)
                needs_init = not db_file.exists() or db_file.stat().st_size == 0

            self._sqlite_conn = sqlite3.connect(target_path, check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row
            # Enable Foreign Key enforcement in SQLite
            self._sqlite_conn.execute("PRAGMA foreign_keys = ON;")

            if needs_init and target_path != ":memory:":
                # Auto-initialize schema & seed data if fresh local database file
                schema_path = config.database_dir / "schema.sql"
                seed_path = config.database_dir / "seed_data.sql"
                if schema_path.exists():
                    cursor = self._sqlite_conn.cursor()
                    for stmt in self._clean_for_sqlite(schema_path.read_text(encoding="utf-8")):
                        cursor.execute(stmt)
                    if seed_path.exists():
                        for stmt in self._clean_for_sqlite(seed_path.read_text(encoding="utf-8")):
                            cursor.execute(stmt)
                    self._sqlite_conn.commit()

        return self._sqlite_conn

    def test_connection(self) -> Tuple[bool, str]:
        """Verifies if the database server or test store is reachable."""
        try:
            conn = self.get_connection()
            if self._is_sqlite_mode:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 AS status")
                cursor.fetchone()
                return True, "Connected successfully (SQLite Isolated Mode)"
            else:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1 AS status")
                        cursor.fetchone()
                finally:
                    conn.close()
                return True, f"Connected successfully (MySQL 8.x at {self.cfg.host}:{self.cfg.port}/{self.cfg.name})"
        except Exception as exc:
            return False, f"Connection failed: {str(exc)}"

    def execute_query(
        self,
        sql: str,
        params: Optional[Union[Tuple[Any, ...], Dict[str, Any], List[Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a read query with parameterized inputs and returns results as dictionaries.
        Guarantees SQL injection safety via parameter binding.
        """
        conn = self.get_connection()
        params = params or ()

        if self._is_sqlite_mode:
            cursor = conn.cursor()
            # Normalize MySQL '%s' placeholders to SQLite '?' if in SQLite mode
            normalized_sql = sql.replace("%s", "?")
            cursor.execute(normalized_sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            try:
                # Handle DictCursor for PyMySQL or dictionary=True for mysql.connector
                if hasattr(conn, "cursor"):
                    cursor = conn.cursor()
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    cursor.close()
                    # If results are dicts (DictCursor) or tuples, ensure dict format
                    if results and isinstance(results[0], dict):
                        return results
                    elif results and cursor.description:
                        col_names = [col[0] for col in cursor.description]
                        return [dict(zip(col_names, row)) for row in results]
                    return results if results is not None else []
            finally:
                conn.close()

    def execute_non_query(
        self,
        sql: str,
        params: Optional[Union[Tuple[Any, ...], Dict[str, Any], List[Any]]] = None
    ) -> int:
        """Executes an INSERT, UPDATE, or DELETE statement and returns affected rows."""
        conn = self.get_connection()
        params = params or ()

        if self._is_sqlite_mode:
            cursor = conn.cursor()
            normalized_sql = sql.replace("%s", "?")
            cursor.execute(normalized_sql, params)
            conn.commit()
            return cursor.rowcount
        else:
            try:
                with conn.cursor() as cursor:
                    affected = cursor.execute(sql, params)
                    return affected
            finally:
                conn.close()

    @staticmethod
    def _clean_for_sqlite(sql_text: str) -> List[str]:
        """Translates MySQL DDL/DML script statements to SQLite dialect for isolated test execution."""
        import re
        statements = []
        for raw_stmt in sql_text.split(";"):
            # Strip SQL comments
            lines = [line for line in raw_stmt.splitlines() if not line.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if not stmt:
                continue
            # Skip MySQL database-level administration statements
            if re.match(r"^(CREATE DATABASE|USE)\b", stmt, re.IGNORECASE):
                continue
            # Translate AUTO_INCREMENT primary key
            stmt = re.sub(r"\bINT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", stmt, flags=re.IGNORECASE)
            # Remove MySQL storage engine specification
            stmt = re.sub(r"\s*ENGINE\s*=\s*\w+", "", stmt, flags=re.IGNORECASE)
            # Extract inline secondary INDEX declarations (unsupported inside SQLite CREATE TABLE)
            inline_indexes = re.findall(r",\s*INDEX\s+(\w+)\s*\(([^)]+)\)", stmt, flags=re.IGNORECASE)
            stmt = re.sub(r",\s*INDEX\s+\w+\s*\([^)]+\)", "", stmt, flags=re.IGNORECASE)
            # Strip MySQL-specific ON DUPLICATE KEY UPDATE upserts
            stmt = re.sub(r"\s*ON\s+DUPLICATE\s+KEY\s+UPDATE\s+[^;]+", "", stmt, flags=re.IGNORECASE)
            statements.append(stmt)
            # Recreate extracted secondary indexes as standard SQLite CREATE INDEX statements
            tbl_match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", stmt, re.IGNORECASE)
            if tbl_match and inline_indexes:
                tbl_name = tbl_match.group(1)
                for idx_name, idx_cols in inline_indexes:
                    statements.append(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl_name} ({idx_cols})")
        return statements

    def execute_script(self, sql_script: str) -> None:
        """
        Executes a multi-statement DDL or DML SQL script.
        Used for executing schema.sql and seed_data.sql.
        """
        conn = self.get_connection()
        if self._is_sqlite_mode:
            cursor = conn.cursor()
            for stmt in self._clean_for_sqlite(sql_script):
                cursor.execute(stmt)
            conn.commit()
        else:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql_script)
            finally:
                conn.close()

    @contextlib.contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """ACID transaction context manager with automatic rollback on error."""
        conn = self.get_connection()
        try:
            if not self._is_sqlite_mode and hasattr(conn, "begin"):
                conn.begin()
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if not self._is_sqlite_mode:
                conn.close()

    def close(self):
        """Cleanly releases any persistent connection resources."""
        if self._sqlite_conn is not None:
            self._sqlite_conn.close()
            self._sqlite_conn = None
