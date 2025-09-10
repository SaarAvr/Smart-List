#!/usr/bin/env python3

import sqlite3
import os
from datetime import datetime

class FoodChainDatabase:
    def __init__(self, db_path="data/database.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.initialize_database()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def initialize_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main index table for all food chains
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS main_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_code TEXT UNIQUE NOT NULL,
                chain_name TEXT NOT NULL,
                chain_url TEXT NOT NULL,
                total_branches INTEGER DEFAULT 0,
                last_discovery TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Database initialized at: {self.db_path}")
    
    def add_food_chain(self, chain_code, chain_name, chain_url):
        """Add a food chain to the main index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO main_index 
            (chain_code, chain_name, chain_url, last_discovery) 
            VALUES (?, ?, ?, ?)
        ''', (chain_code, chain_name, chain_url, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_all_food_chains(self):
        """Get all food chains from main index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT chain_code, chain_name, chain_url FROM main_index ORDER BY id')
        food_chains = cursor.fetchall()
        
        conn.close()
        return food_chains
    
    def create_branches_table(self, chain_code):
        """Create branches table for a specific food chain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"branches_{chain_code}"
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_code TEXT UNIQUE NOT NULL,
                branch_name TEXT NOT NULL,
                price_file_name TEXT DEFAULT '',
                promo_file_name TEXT DEFAULT '',
                price_file_date TEXT DEFAULT '',
                promo_file_date TEXT DEFAULT '',
                last_discovery TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_branch(self, chain_code, branch_code, branch_name, price_file="", promo_file=""):
        """Add a branch to a food chain's branches table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"branches_{chain_code}"
        cursor.execute(f'''
            INSERT OR REPLACE INTO {table_name} 
            (branch_code, branch_name, price_file_name, promo_file_name, last_discovery) 
            VALUES (?, ?, ?, ?, ?)
        ''', (branch_code, branch_name, price_file, promo_file, datetime.now().isoformat()))
        
        # Update total branches count in main index
        cursor.execute(f'''
            UPDATE main_index 
            SET total_branches = (
                SELECT COUNT(*) FROM {table_name}
            ), last_update = ?
            WHERE chain_code = ?
        ''', (datetime.now().isoformat(), chain_code))
        
        conn.commit()
        conn.close()
    
    def get_branches(self, chain_code):
        """Get all branches for a specific food chain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"branches_{chain_code}"
        cursor.execute(f'SELECT branch_code, branch_name, price_file_name, promo_file_name FROM {table_name} ORDER BY CAST(branch_code AS INTEGER)')
        branches = cursor.fetchall()
        
        conn.close()
        return branches
    
    def database_exists(self):
        """Check if database file exists"""
        return os.path.exists(self.db_path)
    
    def get_database_status(self):
        """Get database status information"""
        if not self.database_exists():
            return {"exists": False, "food_chains": 0, "total_branches": 0}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count food chains
        cursor.execute('SELECT COUNT(*) FROM main_index')
        food_chains_count = cursor.fetchone()[0]
        
        # Count total branches across all chains
        cursor.execute('SELECT SUM(total_branches) FROM main_index')
        total_branches = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "exists": True,
            "food_chains": food_chains_count,
            "total_branches": total_branches
        }
    
    def create_products_table(self, chain_code, branch_code):
        """Create products table for a specific branch"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"products_{chain_code}_{branch_code}"
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT UNIQUE NOT NULL,
                item_name TEXT NOT NULL,
                manufacturer_name TEXT,
                item_price TEXT,
                unit_of_measure TEXT,
                quantity TEXT,
                price_update_date TEXT,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_promotions_table(self, chain_code, branch_code):
        """Create promotions table for a specific branch"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        promotions_table = f"promotions_{chain_code}_{branch_code}"
        promotion_items_table = f"promotion_items_{chain_code}_{branch_code}"
        
        # Create promotions table
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {promotions_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_id TEXT UNIQUE NOT NULL,
                promotion_description TEXT,
                discounted_price TEXT,
                min_quantity TEXT,
                promotion_end_date TEXT,
                promotion_start_date TEXT,
                max_quantity TEXT,
                discounted_price_per_unit TEXT,
                items_count INTEGER DEFAULT 0,
                related_item_codes TEXT DEFAULT '',
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Backfill columns in case table existed already
        try:
            cursor.execute(f"ALTER TABLE {promotions_table} ADD COLUMN items_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            cursor.execute(f"ALTER TABLE {promotions_table} ADD COLUMN related_item_codes TEXT DEFAULT ''")
        except Exception:
            pass
        
        # Create promotion items table
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {promotion_items_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_id TEXT NOT NULL,
                item_code TEXT NOT NULL,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (promotion_id) REFERENCES {promotions_table} (promotion_id)
            )
        ''')
        # Ensure uniqueness of (promotion_id, item_code) to avoid duplicates across runs
        cursor.execute(f'''CREATE UNIQUE INDEX IF NOT EXISTS idx_{promotion_items_table}_uniq
                           ON {promotion_items_table} (promotion_id, item_code)''')
        
        conn.commit()
        conn.close()
    
    def add_product(self, chain_code, branch_code, product_data):
        """Add a product to a branch's products table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"products_{chain_code}_{branch_code}"
        cursor.execute(f'''
            INSERT OR REPLACE INTO {table_name} 
            (item_code, item_name, manufacturer_name, item_price, unit_of_measure, quantity, price_update_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_data.get('item_code', ''),
            product_data.get('item_name', ''),
            product_data.get('manufacturer_name', ''),
            product_data.get('item_price', ''),
            product_data.get('unit_of_measure', ''),
            product_data.get('quantity', ''),
            product_data.get('price_update_date', '')
        ))
        
        conn.commit()
        conn.close()
    
    def add_promotion(self, chain_code, branch_code, promotion_data):
        """Add a promotion to a branch's promotions table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        promotions_table = f"promotions_{chain_code}_{branch_code}"
        promotion_items_table = f"promotion_items_{chain_code}_{branch_code}"
        
        # Add promotion
        cursor.execute(f'''
            INSERT OR REPLACE INTO {promotions_table} 
            (promotion_id, promotion_description, discounted_price, min_quantity, 
             promotion_end_date, promotion_start_date, max_quantity, discounted_price_per_unit,
             items_count, related_item_codes) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            promotion_data.get('promotion_id', ''),
            promotion_data.get('promotion_description', ''),
            promotion_data.get('discounted_price', ''),
            promotion_data.get('min_quantity', ''),
            promotion_data.get('promotion_end_date', ''),
            promotion_data.get('promotion_start_date', ''),
            promotion_data.get('max_quantity', ''),
            promotion_data.get('discounted_price_per_unit', ''),
            int(promotion_data.get('items_count', 0) or 0),
            promotion_data.get('related_item_codes', '')
        ))
        
        # Add promotion items (avoid duplicates with atomic delete+insert)
        item_codes = promotion_data.get('item_codes', [])
        promotion_id = promotion_data.get('promotion_id', '')
        
        # Clear existing rows for this promotion first (atomic with inserts)
        cursor.execute(f"DELETE FROM {promotion_items_table} WHERE promotion_id = ?", (promotion_id,))
        
        # Insert new items using INSERT OR IGNORE to handle any remaining constraint issues
        for item_code in item_codes:
            cursor.execute(f'''
                INSERT OR IGNORE INTO {promotion_items_table} 
                (promotion_id, item_code) 
                VALUES (?, ?)
            ''', (promotion_id, item_code))
        
        conn.commit()
        conn.close()
    
    def clear_branch_data(self, chain_code, branch_code):
        """Clear all existing products and promotions data for a branch before reprocessing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        products_table = f"products_{chain_code}_{branch_code}"
        promotions_table = f"promotions_{chain_code}_{branch_code}"
        promotion_items_table = f"promotion_items_{chain_code}_{branch_code}"
        
        try:
            cursor.execute(f"DELETE FROM {products_table}")
            cursor.execute(f"DELETE FROM {promotions_table}")
            cursor.execute(f"DELETE FROM {promotion_items_table}")
            conn.commit()
        except Exception as e:
            print(f"Warning: Could not clear data for branch {branch_code}: {e}")
        
        conn.close()
