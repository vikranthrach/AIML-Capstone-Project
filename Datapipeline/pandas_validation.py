from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "books.db"

with sqlite3.connect(DB_PATH) as conn:
    sql_join = """
        WITH ranked AS (
            SELECT
                b.book_id, b.title, b.rating, b.price_inr,
                c.category_id, c.category_name,
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

    # Required pd.read_sql result.
    sql_result = pd.read_sql(sql_join, conn)

    # At least two query results read with pd.read_sql.
    available_result = pd.read_sql(
        "SELECT title, price_gbp, rating FROM books WHERE in_stock = 1 ORDER BY title;",
        conn,
    )
    expensive_result = pd.read_sql(
        "SELECT title, price_gbp, price_inr FROM books WHERE price_gbp BETWEEN 20 AND 40 ORDER BY price_gbp;",
        conn,
    )

    # Recreate JOIN directly from in-memory DataFrames using pd.merge.
    books_df = pd.read_sql(
        "SELECT book_id, title, price_gbp, price_inr, rating, in_stock, category_id FROM books;",
        conn,
    )
    categories_df = pd.read_sql(
        "SELECT category_id, category_name FROM categories;",
        conn,
    )

merged = books_df.merge(categories_df, on="category_id", how="inner")

merged["rn"] = (
    merged.sort_values(["category_id", "rating", "title"], ascending=[True, False, True])
    .groupby("category_id")
    .cumcount()
    + 1
)

merge_result = merged.loc[
    merged["rn"] <= 10,
    ["book_id", "title", "rating", "price_inr", "category_name"]
].sort_values(
    ["category_name", "rating", "title"],
    ascending=[True, False, True]
).reset_index(drop=True)

sql_result = sql_result.reset_index(drop=True)

# Normalize dtypes before comparison because SQLite/pandas can represent integers differently.
for col in ["book_id", "rating"]:
    sql_result[col] = sql_result[col].astype(int)
    merge_result[col] = merge_result[col].astype(int)

sql_result["price_inr"] = sql_result["price_inr"].astype(float)
merge_result["price_inr"] = merge_result["price_inr"].astype(float)

equivalent = sql_result.equals(merge_result)

comparison = sql_result.copy()
comparison["pandas_merge_match"] = merge_result.eq(sql_result).all(axis=1)

print("\nTwo pd.read_sql results:")
print("\n1) In-stock books:")
print(available_result.head(10).to_string(index=False))

print("\n2) Books priced between GBP 20 and GBP 40:")
print(expensive_result.head(10).to_string(index=False))

print("\nJOIN via pd.read_sql:")
print(sql_result.to_string(index=False))

print("\nJOIN reproduced using pd.merge:")
print(merge_result.to_string(index=False))

print(f"\nSQL JOIN and pd.merge equivalent: {equivalent}")

if not equivalent:
    raise AssertionError("SQL JOIN and pd.merge outputs do not match.")

sql_result.to_csv(ROOT / "outputs/join_pd_read_sql.csv", index=False)
merge_result.to_csv(ROOT / "outputs/join_pd_merge.csv", index=False)
comparison.to_csv(ROOT / "outputs/join_side_by_side.csv", index=False)
