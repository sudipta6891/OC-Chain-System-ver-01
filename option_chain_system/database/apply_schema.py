"""
Apply database/schema.sql to the configured PostgreSQL database.
"""

from pathlib import Path
from database.db_connection import DatabaseConnection


def main() -> None:
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")

    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"Schema applied successfully from: {schema_path}")
    except Exception as e:
        conn.rollback()
        print("Schema apply failed:", e)
        raise
    finally:
        cursor.close()
        DatabaseConnection.release_connection(conn)


if __name__ == "__main__":
    main()

