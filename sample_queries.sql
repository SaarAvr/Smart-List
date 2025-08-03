-- Sample SQL Queries for VS Code SQLite Extension
-- Copy and paste these into the query editor

-- 1. Show all food chains
SELECT chain_code, chain_name, chain_url, created_at 
FROM food_chains_metadata;

-- 2. Show branch summary with file status
SELECT 
    branch_code,
    branch_name,
    CASE WHEN price_file_name != '' AND price_file_name IS NOT NULL THEN '✅ Has Price' ELSE '❌ Missing' END as price_status,
    CASE WHEN promo_file_name != '' AND promo_file_name IS NOT NULL THEN '✅ Has Promo' ELSE '❌ Missing' END as promo_status,
    price_file_date,
    promo_file_date
FROM branches 
ORDER BY CAST(branch_code AS INTEGER);

-- 3. Count branches by file status
SELECT 
    'Total Branches' as category, 
    COUNT(*) as count
FROM branches
UNION ALL
SELECT 
    'With Price Files' as category, 
    COUNT(*) as count
FROM branches 
WHERE price_file_name != '' AND price_file_name IS NOT NULL
UNION ALL
SELECT 
    'With Promo Files' as category, 
    COUNT(*) as count
FROM branches 
WHERE promo_file_name != '' AND promo_file_name IS NOT NULL;

-- 4. Show branches missing files
SELECT 
    branch_code,
    branch_name,
    CASE WHEN price_file_name = '' OR price_file_name IS NULL THEN 'Missing Price File' ELSE 'Has Price File' END as price_status,
    CASE WHEN promo_file_name = '' OR promo_file_name IS NULL THEN 'Missing Promo File' ELSE 'Has Promo File' END as promo_status
FROM branches 
WHERE (price_file_name = '' OR price_file_name IS NULL) 
   OR (promo_file_name = '' OR promo_file_name IS NULL)
ORDER BY CAST(branch_code AS INTEGER);

-- 5. Show file name patterns
SELECT 
    branch_code,
    branch_name,
    price_file_name,
    promo_file_name
FROM branches 
WHERE price_file_name != '' AND price_file_name IS NOT NULL
LIMIT 5;

-- 6. Database schema information
SELECT 
    name as table_name,
    sql as create_statement
FROM sqlite_master 
WHERE type = 'table' 
ORDER BY name;

-- 7. Show database statistics
SELECT 
    (SELECT COUNT(*) FROM food_chains_metadata) as food_chains,
    (SELECT COUNT(*) FROM branches) as branches,
    (SELECT COUNT(*) FROM products) as products,
    (SELECT COUNT(*) FROM promotions) as promotions; 