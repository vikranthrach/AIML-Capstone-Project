-- Q1: SELECT + WHERE
SELECT book_id, title, price_gbp, rating, in_stock
FROM books
WHERE in_stock = 1
ORDER BY title;

-- Q2: ORDER BY + LIMIT
SELECT book_id, title, price_gbp, price_inr, rating
FROM books
ORDER BY rating DESC, price_gbp DESC
LIMIT 10;

-- Q3: DISTINCT
SELECT DISTINCT c.category_name
FROM categories c
JOIN books b ON b.category_id = c.category_id
ORDER BY c.category_name;

-- Q4: BETWEEN
SELECT book_id, title, price_gbp, rating
FROM books
WHERE price_gbp BETWEEN 20.00 AND 40.00
ORDER BY price_gbp;

-- Q5: IN
SELECT book_id, title, rating, price_inr
FROM books
WHERE rating IN (4, 5)
ORDER BY rating DESC, title;

-- Q6: JOIN - highest-rated books per category
WITH ranked AS (
    SELECT
        b.book_id,
        b.title,
        b.rating,
        b.price_inr,
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
