"""
load_data.py
Loads the Superstore CSV into a local SQLite database.
Run this once to create data/superstore.db
"""

import pandas as pd
import sqlite3
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "Sample_-_Superstore.csv")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "superstore.db")


def clean_column_names(df):
    """Convert 'Order Date' -> 'order_date' etc. so SQL is easier to write/read."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return df


def load():
    print(f"Reading CSV from {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, encoding="latin1")

    df = clean_column_names(df)

    # Convert date columns to proper ISO format (YYYY-MM-DD) for SQLite
    df["order_date"] = pd.to_datetime(df["order_date"], format="%d-%m-%Y").dt.strftime("%Y-%m-%d")
    df["ship_date"] = pd.to_datetime(df["ship_date"], format="%d-%m-%Y").dt.strftime("%Y-%m-%d")

    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print("Columns:", df.columns.tolist())

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("orders", conn, if_exists="replace", index=False)

    # Quick sanity check
    check = pd.read_sql("SELECT COUNT(*) as total_rows FROM orders", conn)
    print(f"Rows in SQLite table 'orders': {check['total_rows'][0]}")

    conn.close()
    print(f"Done. Database saved to {DB_PATH}")


if __name__ == "__main__":
    load()
