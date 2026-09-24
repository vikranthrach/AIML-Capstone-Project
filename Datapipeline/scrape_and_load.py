"""
End-to-end BooksToScrape -> cleaned DataFrame -> normalized SQLite pipeline.

Run:
    python scrape_and_load.py

The script scrapes the first 5 pages of the All Products catalogue,
which is sufficient for >= 60 books.
"""

from pathlib import Path
import re
import sqlite3
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
PAGES = 5
GBP_TO_INR = 105.50

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "books.db"
SCHEMA_PATH = ROOT / "schema.sql"


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; DataPipelineAssignment/1.0)"},
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def scrape_books() -> pd.DataFrame:
    rows = []

    for page_no in range(1, PAGES + 1):
        soup = get_soup(BASE_URL.format(page_no))

        for product in soup.select("article.product_pod"):
            title_tag = product.select_one("h3 a")
            price_tag = product.select_one(".price_color")
            rating_tag = product.select_one("p.star-rating")
            availability_tag = product.select_one(".availability")

            title = title_tag.get("title", "").strip() if title_tag else ""
            price_text = price_tag.get_text(" ", strip=True) if price_tag else ""
            rating_text = ""
            if rating_tag:
                classes = rating_tag.get("class", [])
                rating_text = next(
                    (c for c in classes if c.lower() in {"one", "two", "three", "four", "five"}),
                    ""
                ).title()
            availability = availability_tag.get_text(" ", strip=True) if availability_tag else ""

            # Category is available from the book detail page breadcrumb.
            href = title_tag.get("href") if title_tag else None
            category = ""
            if href:
                detail_url = requests.compat.urljoin(BASE_URL.format(page_no), href)
                detail_soup = get_soup(detail_url)
                crumbs = detail_soup.select("ul.breadcrumb li a")
                # Breadcrumb is Home > Books > Category > Title
                if len(crumbs) >= 3:
                    category = crumbs[-1].get_text(strip=True)

            rows.append(
                {
                    "title": title,
                    "price_as_listed": price_text,
                    "star_rating": rating_text,
                    "availability": availability,
                    "category": category,
                }
            )

    return pd.DataFrame(rows)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Numeric parsing: invalid values become NaN and are median-imputed.
    out["price_gbp"] = pd.to_numeric(
        out["price_as_listed"].astype(str).str.replace(r"[^\d.]", "", regex=True),
        errors="coerce",
    )
    if out["price_gbp"].isna().all():
        raise ValueError("No valid prices were parsed.")
    out["price_gbp"] = out["price_gbp"].fillna(out["price_gbp"].median())

    rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    out["rating"] = out["star_rating"].map(rating_map)
    if out["rating"].isna().any():
        median_rating = int(round(out["rating"].median()))
        out["rating"] = out["rating"].fillna(median_rating).astype(int)
    out["rating"] = out["rating"].clip(1, 5).astype(int)

    # Availability contains "In stock" or "Out of stock".
    out["in_stock"] = (
        out["availability"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.startswith("in stock")
    ).astype(bool)

    # Required categorical fields: drop rows if unrecoverable.
    before = len(out)
    out["title"] = out["title"].astype(str).str.strip()
    out["category"] = out["category"].astype(str).str.strip()
    out = out[(out["title"] != "") & (out["category"] != "")]
    dropped = before - len(out)

    out["price_inr"] = (out["price_gbp"] * GBP_TO_INR).round(2)

    # Keep clean columns only.
    out = out[
        ["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]
    ].reset_index(drop=True)

    print(f"Rows dropped because title/category could not be recovered: {dropped}")
    print(f"Clean rows: {len(out)}")

    if len(out) < 60:
        raise RuntimeError(f"Acceptance criterion failed: only {len(out)} rows.")

    if out["category"].nunique() < 3:
        raise RuntimeError("Acceptance criterion failed: fewer than 3 categories.")

    return out


def create_database(df: pd.DataFrame) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema)

        categories = pd.DataFrame({"category_name": sorted(df["category"].unique())})
        categories.to_sql("categories", conn, if_exists="append", index=False)

        category_ids = pd.read_sql(
            "SELECT category_id, category_name FROM categories", conn
        )

        books = df.merge(
            category_ids, left_on="category", right_on="category_name", how="left"
        )

        books = books[
            ["title", "price_gbp", "price_inr", "rating", "in_stock", "category_id"]
        ]
        books.to_sql("books", conn, if_exists="append", index=False)

    print(f"SQLite database created: {DB_PATH}")


def main():
    raw = scrape_books()
    raw.to_csv(ROOT / "raw_books.csv", index=False)
    cleaned = clean_data(raw)
    cleaned.to_csv(ROOT / "cleaned_books.csv", index=False)
    create_database(cleaned)


if __name__ == "__main__":
    main()
