from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "books.db"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

QUERIES = {
    "query_01_select_where": """
        SELECT book_id, title, price_gbp, rating, in_stock
        FROM books
        WHERE in_stock = 1
        ORDER BY title;
    """,
    "query_02_order_by_limit": """
        SELECT book_id, title, price_gbp, price_inr, rating
        FROM books
        ORDER BY rating DESC, price_gbp DESC
        LIMIT 10;
    """,
    "query_03_distinct": """
        SELECT DISTINCT c.category_name
        FROM categories c
        JOIN books b ON b.category_id = c.category_id
        ORDER BY c.category_name;
    """,
    "query_04_between": """
        SELECT book_id, title, price_gbp, rating
        FROM books
        WHERE price_gbp BETWEEN 20.00 AND 40.00
        ORDER BY price_gbp;
    """,
    "query_05_in": """
        SELECT book_id, title, rating, price_inr
        FROM books
        WHERE rating IN (4, 5)
        ORDER BY rating DESC, title;
    """,
    "query_06_join_top_rated_per_category": """
        WITH ranked AS (
            SELECT
                b.book_id, b.title, b.rating, b.price_inr,
                c.category_name,
                ROW_NUMBER() OVER (
                    PARTITION BY c.category_id
                    ORDER BY b.rating DESC, b.title
                ) AS rn
            FROM books b
            JOIN categories c ON b.category_id = c.category_id
        )
        SELECT book_id, title, rating, price_inr, category_name
        FROM ranked
        WHERE rn <= 10
        ORDER BY category_name, rating DESC, title;
    """
}

with sqlite3.connect(DB_PATH) as conn:
    for name, sql in QUERIES.items():
        df = pd.read_sql(sql, conn)
        print("\n" + "=" * 80)
        print(name)
        print("=" * 80)
        print(sql.strip())
        print("\nOUTPUT:")
        print(df.to_string(index=False))
        df.to_csv(OUT / f"{name}.csv", index=False)
        (OUT / f"{name}.sql").write_text(sql.strip() + "\n", encoding="utf-8")
