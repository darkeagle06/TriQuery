# TriQuery: MySQL 8.x Database Setup Instructions

This document provides clear instructions for setting up the relational database layer for TriQuery in MySQL 8.x.

---

## 1. Prerequisites

- **MySQL Server 8.x** installed and running on your local machine or Docker.
- A MySQL user with privileges to create databases and tables (e.g., `root` or a dedicated `triquery_user`).
- Python 3.13 with the project dependencies installed.

---

## 2. Option A: Automated Setup via TriQuery CLI (Recommended)

1. Ensure your `.env` file exists at the root of `TriQuery/`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your MySQL credentials:
   ```env
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_NAME=triquery_db
   DB_USER=root
   DB_PASSWORD=your_actual_password
   ```
3. Run the automated database setup script:
   ```bash
   python -m src.engines.relational.setup_db
   ```
   This script will:
   - Connect to your MySQL 8.x server.
   - Create `triquery_db` if it does not already exist.
   - Execute [`database/schema.sql`](file:///c:/COLLAGE%20RELEATED/MY_CODES/sql/TriQuery/database/schema.sql) (all 7 tables, PKs, FKs, indexes).
   - Execute [`database/seed_data.sql`](file:///c:/COLLAGE%20RELEATED/MY_CODES/sql/TriQuery/database/seed_data.sql) (seed hackathons, colleges, teams, projects, awards).
   - Verify table row counts.

---

## 3. Option B: Manual Setup via MySQL Command Line

If you prefer using the MySQL command-line client:

1. Log in to MySQL:
   ```bash
   mysql -u root -p
   ```
2. Execute the schema:
   ```sql
   SOURCE database/schema.sql;
   ```
3. Load the seed dataset:
   ```sql
   SOURCE database/seed_data.sql;
   ```
4. Verify the setup:
   ```sql
   USE triquery_db;
   SHOW TABLES;
   SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = 'triquery_db';
   ```

---

## 4. Option C: Manual Setup via MySQL Workbench

1. Launch **MySQL Workbench 8.0**.
2. Open your local MySQL connection.
3. Open `database/schema.sql` (`File -> Open SQL Script...`) and click the **Execute (Lightning bolt)** button.
4. Open `database/seed_data.sql` and execute it.
5. In the Schemas tab on the left, right-click and click **Refresh All**. Verify that `triquery_db` appears with all 7 tables.

---

## 5. Offline / Standalone Testing Mode

If you are running automated tests or running on a machine without a live MySQL 8.x server:
Set `DB_TEST_SQLITE_FALLBACK=true` in `.env` (or pass `--driver sqlite` in the CLI).
TriQuery will use an isolated in-memory SQLite relational replica, allowing all relational algebra tests and CLI queries to run immediately with zero external dependencies.
