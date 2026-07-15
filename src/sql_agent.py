"""
sql_agent.py
The core agent: takes a natural language question, generates SQL using Claude,
runs it against the database, and returns a plain-English answer.

Requires ANTHROPIC_API_KEY to be set as an environment variable.
"""

import os
import re
import sqlite3
import pandas as pd
from groq import Groq

from schema_prompt import build_system_prompt

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "superstore.db")
MODEL = "llama-3.3-70b-versatile"

client = Groq()  # reads GROQ_API_KEY from environment automatically

# Keywords that should never appear in a query this app runs.
# This is a HARD code-level block — it does not depend on the LLM behaving.
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "TRUNCATE", "REPLACE", "ATTACH", "PRAGMA"
]


class UnsafeQueryError(Exception):
    """Raised when generated SQL fails the safety check."""
    pass


def validate_sql(sql: str) -> None:
    """
    Guardrail: rejects any SQL that isn't a plain SELECT statement.
    Raises UnsafeQueryError if the query looks unsafe, instead of ever
    letting it reach the database.
    """
    cleaned = sql.strip().rstrip(";").strip()

    # Must start with SELECT
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise UnsafeQueryError(
            f"Rejected: query does not start with SELECT.\nQuery was: {sql}"
        )

    # Must not contain any forbidden keyword anywhere in the query
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", cleaned, re.IGNORECASE):
            raise UnsafeQueryError(
                f"Rejected: query contains forbidden keyword '{keyword}'.\nQuery was: {sql}"
            )

    # Must not contain multiple statements (semicolon followed by more SQL)
    if ";" in cleaned:
        raise UnsafeQueryError(
            f"Rejected: multiple statements are not allowed.\nQuery was: {sql}"
        )


def generate_sql(question: str, history: list = None) -> str:
    """
    Sends the user's question + schema context to the LLM, gets back a SQL query.
    `history` (optional): list of {"question": ..., "sql": ...} from prior turns
    in this conversation, so follow-up questions like "what about the West region?"
    can be resolved using earlier context.
    """
    system_prompt = build_system_prompt()

    context_block = ""
    if history:
        context_lines = []
        for turn in history[-3:]:  # last 3 turns is enough context, keeps prompt small
            context_lines.append(f'Q: {turn["question"]}\nSQL used: {turn["sql"]}')
        context_block = (
            "Here is the recent conversation for context (the new question may "
            "refer back to it, e.g. 'what about the West region instead?'):\n\n"
            + "\n\n".join(context_lines)
            + "\n\n---\n\n"
        )

    user_message = f"{context_block}New question: {question}"

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )

    sql = response.choices[0].message.content.strip()

    # Safety net: strip markdown fences if the model adds them despite instructions
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


def run_sql(sql: str) -> pd.DataFrame:
    """
    Executes the SQL query against the local SQLite database.
    Opens the connection in READ-ONLY mode as a second layer of defense
    (in addition to the validate_sql keyword check).
    """
    # file:...?mode=ro forces SQLite to refuse any write operation at the
    # database engine level, even if a bad query somehow got past validate_sql
    db_uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        result = pd.read_sql(sql, conn)
    finally:
        conn.close()
    return result


def explain_result(question: str, sql: str, result_df: pd.DataFrame) -> str:
    """
    Sends the query result back to Claude and asks for a plain-English answer.
    """
    # Convert result to a compact string representation for the prompt
    result_str = result_df.to_string(index=False, max_rows=20)

    prompt = f"""The user asked: "{question}"

This SQL query was run:
{sql}

It returned this result:
{result_str}

Write a short, clear, plain-English answer to the user's question based on this result.
Include the specific number(s) from the result. Keep it to 1-3 sentences. Do not mention SQL or databases."""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=300,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()


def ask(question: str, history: list = None) -> dict:
    """
    Full pipeline: question -> SQL -> validate -> execute -> plain-English answer.
    `history`: optional list of prior {"question", "sql"} turns for follow-up context.
    Returns a dict with all intermediate steps (useful for the UI, which
    will show the SQL alongside the answer to build trust).
    """
    sql = generate_sql(question, history=history)

    # Guardrail: this raises UnsafeQueryError and stops here if the query
    # isn't a safe, single SELECT statement. Nothing unsafe reaches the DB.
    validate_sql(sql)

    result_df = run_sql(sql)
    answer = explain_result(question, sql, result_df)

    return {
        "question": question,
        "sql": sql,
        "result": result_df,
        "answer": answer
    }


if __name__ == "__main__":
    # Quick manual test
    test_question = "Which product category has the worst average profit margin when discount is 40% or more?"
    output = ask(test_question)
    print("QUESTION:", output["question"])
    print("\nGENERATED SQL:\n", output["sql"])
    print("\nRESULT:\n", output["result"])
    print("\nANSWER:\n", output["answer"])
