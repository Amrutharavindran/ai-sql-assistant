"""
schema_prompt.py
Builds a schema-aware system prompt by introspecting the actual SQLite database.
This is what lets Claude write correct SQL for ANY question, not just ones we
hardcoded in advance.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "superstore.db")


def get_schema_description(db_path=DB_PATH, sample_rows=3):
    """
    Introspects the SQLite table and returns:
    1. Column names + types
    2. A few real sample rows (helps Claude understand actual values,
       e.g. that 'region' contains 'West'/'East', not full country names)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get column info
    cursor.execute("PRAGMA table_info(orders)")
    columns = cursor.fetchall()  # (cid, name, type, notnull, default, pk)

    column_lines = [f"  - {col[1]} ({col[2]})" for col in columns]
    column_block = "\n".join(column_lines)

    # Get a few sample rows so Claude sees real values, not just names
    col_names = [col[1] for col in columns]
    cursor.execute(f"SELECT * FROM orders LIMIT {sample_rows}")
    rows = cursor.fetchall()

    sample_lines = []
    for row in rows:
        row_dict = dict(zip(col_names, row))
        sample_lines.append(str(row_dict))
    sample_block = "\n".join(sample_lines)

    conn.close()

    return column_block, sample_block


def build_system_prompt():
    """
    Assembles the full system prompt sent to Claude before every SQL-generation call.
    """
    column_block, sample_block = get_schema_description()

    prompt = f"""You are a SQL expert helping analyze a retail orders dataset.

The database has ONE table called "orders" with these columns:
{column_block}

Here are {3} real sample rows so you understand the actual data values:
{sample_block}

RULES:
1. Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
2. Only use the "orders" table and the columns listed above — do not invent column names.
3. Return ONLY the raw SQL query. No explanation, no markdown code fences, no preamble.
4. Use SQLite syntax (e.g. use strftime() for date parts, not YEAR()/MONTH()).
5. When the question is about "profit margin", calculate it as (profit / sales) * 100.
6. If the question is ambiguous, make a reasonable assumption and proceed rather than asking for clarification.
"""
    return prompt


if __name__ == "__main__":
    # Quick test to see what the prompt looks like
    print(build_system_prompt())
