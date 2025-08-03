#!/usr/bin/env python3
"""
Database Visualization Script
Shows the content of the food chain database in a readable format
"""

import sqlite3
import datetime
from database_setup import FoodChainDatabase

def visualize_database():
    """Display database content in a nice format"""
    
    # Connect to database
    db = FoodChainDatabase()
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    print("🏢 FOOD CHAIN DATABASE VISUALIZATION")
    print("=" * 50)
    
    # 1. Food Chain Metadata
    print("\n📊 FOOD CHAIN METADATA:")
    cursor.execute("SELECT chain_code, actual_chain_code, chain_name, chain_url, created_at FROM food_chains_metadata")
    chains = cursor.fetchall()
    
    for chain in chains:
        chain_code, actual_code, name, url, created = chain
        print(f"  🏪 Chain Code: {chain_code}")
        if actual_code:
            print(f"  🔢 Actual Code: {actual_code}")
        print(f"  📝 Name: {name}")
        print(f"  🔗 URL: {url}")
        print(f"  📅 Created: {created}")
    
    # 2. Branch Summary
    print(f"\n🏪 BRANCH SUMMARY:")
    cursor.execute("SELECT COUNT(*) FROM branches")
    total_branches = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM branches WHERE price_file_name != '' AND price_file_name IS NOT NULL")
    branches_with_price = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM branches WHERE promo_file_name != '' AND promo_file_name IS NOT NULL") 
    branches_with_promo = cursor.fetchone()[0]
    
    print(f"  📈 Total Branches: {total_branches}")
    print(f"  💰 Branches with Price Files: {branches_with_price}")
    print(f"  🎯 Branches with Promo Files: {branches_with_promo}")
    print(f"  ❌ Missing Price Files: {total_branches - branches_with_price}")
    print(f"  ❌ Missing Promo Files: {total_branches - branches_with_promo}")
    
    # 3. Detailed Branch List
    print(f"\n📋 DETAILED BRANCH LIST:")
    print("=" * 80)
    print(f"{'Code':<4} {'Name':<25} {'Price':<6} {'Promo':<6} Price File Date")
    print("-" * 80)
    
    cursor.execute("""
        SELECT branch_code, branch_name, price_file_name, price_file_date, 
               promo_file_name, promo_file_date 
        FROM branches 
        ORDER BY CAST(branch_code AS INTEGER)
    """)
    
    branches = cursor.fetchall()
    
    for branch in branches:
        code, name, price_file, price_date, promo_file, promo_date = branch
        
        # Truncate name if too long
        display_name = name[:22] + "..." if len(name) > 25 else name
        
        # Status indicators
        price_status = "✅" if price_file and price_file.strip() else "❌"
        promo_status = "✅" if promo_file and promo_file.strip() else "❌"
        
        # Format date (convert 202507271024 to 2025-07-27 10:24)
        formatted_date = ""
        if price_date and len(price_date) == 12:
            try:
                year = price_date[:4]
                month = price_date[4:6] 
                day = price_date[6:8]
                hour = price_date[8:10]
                minute = price_date[10:12]
                formatted_date = f"{year}-{month}-{day} {hour}:{minute}"
            except:
                formatted_date = price_date
        
        print(f"{code:<4} {display_name:<25} {price_status:<6} {promo_status:<6} {formatted_date}")
    
    # 4. File Examples
    print(f"\n📁 FILE EXAMPLES:")
    cursor.execute("""
        SELECT price_file_name, promo_file_name 
        FROM branches 
        WHERE price_file_name != '' AND promo_file_name != ''
        LIMIT 3
    """)
    
    examples = cursor.fetchall()
    for i, (price_file, promo_file) in enumerate(examples, 1):
        print(f"  Example {i}:")
        print(f"    💰 Price: {price_file}")
        print(f"    🎯 Promo: {promo_file}")
    
    # 5. Missing Files Analysis
    print(f"\n❌ BRANCHES MISSING FILES:")
    cursor.execute("""
        SELECT branch_code, branch_name,
               CASE WHEN price_file_name = '' OR price_file_name IS NULL THEN 'Missing Price' ELSE 'Has Price' END,
               CASE WHEN promo_file_name = '' OR promo_file_name IS NULL THEN 'Missing Promo' ELSE 'Has Promo' END
        FROM branches 
        WHERE (price_file_name = '' OR price_file_name IS NULL) 
           OR (promo_file_name = '' OR promo_file_name IS NULL)
        ORDER BY CAST(branch_code AS INTEGER)
    """)
    
    missing = cursor.fetchall()
    if missing:
        for branch in missing:
            code, name, price_status, promo_status = branch
            print(f"  🏪 {code}: {name}")
            print(f"    💰 {price_status}")
            print(f"    🎯 {promo_status}")
    else:
        print("  🎉 All branches have complete file information!")
    
    # 6. Database Size
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM promotions")
    promotion_count = cursor.fetchone()[0]
    
    print(f"\n📊 DATABASE SIZE:")
    print(f"  🏪 Food Chains: {len(chains)}")
    print(f"  🏢 Branches: {total_branches}")
    print(f"  🛒 Products: {product_count}")
    print(f"  🎯 Promotions: {promotion_count}")
    
    conn.close()
    print("\n✅ Database visualization complete!")

if __name__ == "__main__":
    visualize_database() 