#!/usr/bin/env python3
"""
Hierarchical Database Navigator
Navigate through: Main → Food Chains → Branches → Products
"""

import sqlite3
import json
from database_hierarchical import HierarchicalFoodDatabase

class DatabaseNavigator:
    def __init__(self):
        self.db = HierarchicalFoodDatabase()
        self.db_path = self.db.db_path
    
    def show_main_index(self):
        """Show main index with all food chains"""
        print("🏠 MAIN INDEX - All Food Chains")
        print("=" * 50)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get metadata
        try:
            cursor.execute('SELECT * FROM main_index_metadata WHERE id = 1')
            meta = cursor.fetchone()
            if meta:
                print(f"📍 Root URL: {meta[1]}")
                print(f"📊 Total Chains: {meta[2]}")
                print(f"🕒 Last Discovery: {meta[3]}")
        except:
            print("⚠️ Metadata not available")
        
        print("\n🏪 Food Chains:")
        try:
            cursor.execute('SELECT chain_code, chain_name, chain_url FROM main_index ORDER BY chain_code')
            chains = cursor.fetchall()
            
            for i, (code, name, url) in enumerate(chains, 1):
                print(f"   {i}. {code}: {name}")
                print(f"      URL: {url}")
        except Exception as e:
            print(f"❌ Error reading chains: {str(e)}")
        
        conn.close()
        return [row[0] for row in chains] if 'chains' in locals() else []
    
    def show_chain_branches(self, chain_code):
        """Show all branches for a food chain"""
        print(f"\n🏪 FOOD CHAIN: {chain_code}")
        print("=" * 50)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get chain metadata
        metadata_table = f"chain_{chain_code}_branches_metadata"
        try:
            cursor.execute(f'SELECT * FROM {metadata_table} WHERE id = 1')
            meta = cursor.fetchone()
            if meta:
                print(f"📍 Chain Name: {meta[1]}")
                print(f"🔗 Chain URL: {meta[3]}")
                print(f"📊 Total Branches: {meta[4]}")
                print(f"🕒 Last Update: {meta[5]}")
        except Exception as e:
            print(f"⚠️ Chain metadata not available: {str(e)}")
        
        # Get branches
        branches_table = f"chain_{chain_code}_branches"
        print(f"\n🏢 Branches:")
        try:
            cursor.execute(f'''
                SELECT branch_code, branch_name, price_file_name, promo_file_name, address
                FROM {branches_table} ORDER BY CAST(branch_code AS INTEGER)
            ''')
            branches = cursor.fetchall()
            
            for i, (b_code, b_name, price_file, promo_file, address) in enumerate(branches, 1):
                print(f"   {i}. Branch {b_code}: {b_name}")
                if address:
                    print(f"      📍 Address: {address}")
                print(f"      📄 Price File: {price_file or 'N/A'}")
                print(f"      🎯 Promo File: {promo_file or 'N/A'}")
                print()
        except Exception as e:
            print(f"❌ Error reading branches: {str(e)}")
        
        conn.close()
        return [row[0] for row in branches] if 'branches' in locals() else []
    
    def show_branch_products(self, chain_code, branch_code, limit=10):
        """Show products for a specific branch"""
        print(f"\n📦 BRANCH PRODUCTS: Chain {chain_code}, Branch {branch_code}")
        print("=" * 70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get branch metadata
        products_table = f"branch_{chain_code}_{branch_code}_products"
        metadata_table = f"{products_table}_metadata"
        
        try:
            cursor.execute(f'SELECT * FROM {metadata_table} WHERE id = 1')
            meta = cursor.fetchone()
            if meta:
                print(f"🏪 Branch Name: {meta[3]}")
                print(f"📊 Total Products: {meta[6]:,}")
                print(f"📄 Latest Price File: {meta[4]}")
                print(f"🕒 Last Update: {meta[7]}")
        except Exception as e:
            print(f"⚠️ Branch metadata not available: {str(e)}")
        
        # Get sample products
        print(f"\n📋 Sample Products (showing {limit}):")
        try:
            cursor.execute(f'''
                SELECT item_code, item_name, manufacturer_name, item_price, 
                       unit_of_measure, price_update_date
                FROM {products_table} 
                ORDER BY CAST(item_price AS REAL) DESC 
                LIMIT {limit}
            ''')
            products = cursor.fetchall()
            
            print(f"{'Item Code':<15} {'Product Name':<40} {'Price':<10} {'Manufacturer':<20}")
            print("-" * 90)
            
            for code, name, manufacturer, price, unit, update_date in products:
                name_short = name[:37] + "..." if len(name) > 40 else name
                manufacturer_short = manufacturer[:17] + "..." if len(manufacturer) > 20 else manufacturer
                print(f"{code:<15} {name_short:<40} ₪{price:<9.2f} {manufacturer_short:<20}")
                
        except Exception as e:
            print(f"❌ Error reading products: {str(e)}")
        
        conn.close()
    
    def navigate_full_path(self):
        """Navigate through the complete hierarchy"""
        print("🚀 HIERARCHICAL DATABASE NAVIGATION")
        print("=" * 60)
        
        # Step 1: Show main index
        chains = self.show_main_index()
        
        if not chains:
            print("❌ No food chains found")
            return
        
        # Step 2: Show first chain's branches
        chain_code = chains[0]  # Use first available chain
        branches = self.show_chain_branches(chain_code)
        
        if not branches:
            print("❌ No branches found")
            return
        
        # Step 3: Show first branch's products
        branch_code = branches[0]  # Use first available branch
        self.show_branch_products(chain_code, branch_code, limit=15)
        
        print(f"\n🎯 NAVIGATION COMPLETE!")
        print(f"📍 Path: Main Index → {chain_code} → Branch {branch_code} → Products")

if __name__ == "__main__":
    navigator = DatabaseNavigator()
    navigator.navigate_full_path() 