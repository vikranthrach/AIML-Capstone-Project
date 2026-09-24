# Data Pipeline Module

## Objective

This module implements a complete catalog-style ETL pipeline:

**BooksToScrape → scrape → clean → convert currency → normalize → SQLite → SQL → pandas**

## Data source

The pipeline uses the public scraping-practice site:

`https://books.toscrape.com/`

It scrapes the first **5 pages** of the All Products catalogue. This scope is intended to produce at least 60 books and naturally covers multiple categories.

## Required fixed currency rate

The assignment-defined baseline is:

**1 GBP = 105.50 INR**

`price_inr` is calculated only as:

```text
price_inr = price_gbp * 105.50
```

No live currency API is required or used.

## Cleaning decisions

### Price

Examples such as:

```text
£51.77
```

are converted to:

```text
51.77
```

Non-numeric characters are removed and the result is parsed as a float.

If a price cannot be parsed, it becomes null temporarily and is replaced with the median valid `price_gbp`.

### Rating

The website's text ratings are mapped as follows:

```text
One   -> 1
Two   -> 2
Three -> 3
Four  -> 4
Five  -> 5
```

If an unexpected rating is encountered, the median parsed rating is used.

### Availability

Values beginning with `In stock` are converted to `True`; other availability values are treated as `False`.

### Missing title/category

Title and category are required dimensions for this normalized catalog. A row whose title or category cannot be recovered is dropped rather than creating an unusable database record. The script prints the number of dropped rows.

## Database design

The database contains two normalized tables.

### categories

- `category_id` — primary key
- `category_name` — unique category name

### books

- `book_id` — primary key
- `title`
- `price_gbp`
- `price_inr`
- `rating`
- `in_stock`
- `category_id` — foreign key to `categories.category_id`

The foreign-key relationship is enabled using SQLite `PRAGMA foreign_keys = ON`.

## Installation

Python 3.9+ is recommended.

```bash
cd data_pipeline
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the pipeline

```bash
python scrape_and_load.py
```

This creates:

- `raw_books.csv`
- `cleaned_books.csv`
- `books.db`

The script fails explicitly if the final cleaned dataset has fewer than 60 rows or fewer than 3 categories.

## Execute SQL queries

```bash
python run_queries.py
```

This executes six queries and saves both SQL and CSV outputs in `outputs/`.

The queries collectively demonstrate:

- `SELECT`
- `WHERE`
- `ORDER BY`
- `LIMIT`
- `DISTINCT`
- `BETWEEN`
- `IN`
- `JOIN`

## pandas validation

```bash
python pandas_validation.py
```

This:

1. Reads multiple SQL results using `pd.read_sql()`.
2. Reads the `books` and `categories` tables into pandas.
3. Reproduces the required JOIN using `pd.merge()`.
4. Applies the same per-category top-10 ranking logic in pandas.
5. Compares the SQL JOIN result with the pandas result.
6. Raises an error if they are not equivalent.
7. Saves the side-by-side comparison to `outputs/join_side_by_side.csv`.

## Expected acceptance checks

After running:

```bash
python scrape_and_load.py
```

verify:

```text
Clean rows >= 60
Distinct categories >= 3
price_gbp is numeric
price_inr is numeric
rating is integer 1-5
in_stock is boolean before SQLite storage
price_inr = price_gbp * 105.50
```

SQLite stores booleans as integers (`0`/`1`), which is standard SQLite behavior.

## Git requirement

The repository-level history must show a feature branch with at least two commits and a merge back into `main`.

Example:

```bash
git checkout main
git checkout -b feature/data-pipeline

git add data_pipeline/
git commit -m "Add book scraping and cleaning pipeline"

git add data_pipeline/
git commit -m "Add SQLite queries and pandas validation"

git checkout main
git merge feature/data-pipeline
```

Verify:

```bash
git log --oneline --graph --all
```

Do not squash the two feature commits if the evaluator needs to see the branch history explicitly.

## Notes

The generated SQLite database is reproducible. If the database is not committed, the evaluator can recreate it with:

```bash
python scrape_and_load.py
```

Network access is required only when executing the scraping step because the source site is live.
