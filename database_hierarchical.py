import sqlite3
import os
import json
from datetime import datetime

class HierarchicalFoodDatabase:
    def __init__(self, db_path="data/hierarchical_food_chains.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        print(f"✅ Database will be created at: {self.db_path}")
    
    def init_database(self):
        """Initialize the hierarchical database structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ========================================
        # MAIN INDEX TABLE
        # ========================================
        # Metadata: Root URL, total number of food chains
        # Rows: One row per food chain
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS main_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_code TEXT UNIQUE NOT NULL,
                chain_name TEXT NOT NULL,
                chain_url TEXT NOT NULL,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Table metadata (stored as JSON for flexibility)
                table_metadata TEXT DEFAULT '{}',
                
                UNIQUE(chain_code)
            )
        ''')
        
        # Metadata table for main_index
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS main_index_metadata (
                id INTEGER PRIMARY KEY,
                root_url TEXT NOT NULL,
                total_chains INTEGER DEFAULT 0,
                last_discovery_update TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        ''')
        
        # Create metadata for main_index table
        cursor.execute('''
            INSERT OR REPLACE INTO main_index_metadata (
                id, root_url, total_chains, last_discovery_update
            ) VALUES (1, ?, ?, ?)
        ''', (
            'https://www.gov.il/he/pages/cpfta_prices_regulations',
            0,  # Will be updated when we populate
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        print("✅ Hierarchical database structure initialized")
    
    def create_chain_table(self, chain_code, chain_name, chain_url):
        """Create a food chain table with metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table name for this chain's branches
        table_name = f"chain_{chain_code}_branches"
        
        # Create branches table for this chain
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_code TEXT UNIQUE NOT NULL,
                branch_name TEXT NOT NULL,
                
                -- File tracking (for downloads)
                price_file_name TEXT,
                price_file_date TEXT,
                promo_file_name TEXT,
                promo_file_date TEXT,
                
                -- Location info (placeholders for future)
                address TEXT DEFAULT '',
                coordinates TEXT DEFAULT '',
                
                -- Metadata
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(branch_code)
            )
        ''')
        
        # Create metadata table for this chain
        metadata_table = f"{table_name}_metadata"
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {metadata_table} (
                id INTEGER PRIMARY KEY,
                chain_name TEXT NOT NULL,
                chain_code TEXT NOT NULL,
                chain_url TEXT NOT NULL,
                total_branches INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        ''')
        
        # Insert metadata
        cursor.execute(f'''
            INSERT OR REPLACE INTO {metadata_table} (
                id, chain_name, chain_code, chain_url, total_branches, last_update
            ) VALUES (1, ?, ?, ?, 0, ?)
        ''', (chain_name, chain_code, chain_url, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print(f"✅ Created chain table: {table_name}")
        return table_name
    
    def create_branch_table(self, chain_code, branch_code, branch_name, price_file=None, promo_file=None):
        """Create a branch table with metadata for products"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table name for this branch's products
        table_name = f"branch_{chain_code}_{branch_code}_products"
        
        # Create products table for this branch
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Product identification
                item_code TEXT NOT NULL,
                item_name TEXT NOT NULL,
                manufacturer_name TEXT,
                
                -- Pricing information
                item_price REAL NOT NULL,
                unit_of_measure TEXT,
                quantity REAL,
                
                -- Metadata
                price_update_date TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create metadata table for this branch
        metadata_table = f"{table_name}_metadata"
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {metadata_table} (
                id INTEGER PRIMARY KEY,
                chain_code TEXT NOT NULL,
                branch_code TEXT NOT NULL,
                branch_name TEXT NOT NULL,
                latest_price_file TEXT DEFAULT '',
                latest_promo_file TEXT DEFAULT '',
                total_products INTEGER DEFAULT 0,
                total_promotions INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        ''')
        
        # Insert metadata
        cursor.execute(f'''
            INSERT OR REPLACE INTO {metadata_table} (
                id, chain_code, branch_code, branch_name, 
                latest_price_file, latest_promo_file, last_update
            ) VALUES (1, ?, ?, ?, ?, ?, ?)
        ''', (
            chain_code, branch_code, branch_name,
            price_file or '', promo_file or '',
            datetime.now().isoformat()
        ))
        
        # ========================================
        # CREATE PROMOTIONS TABLE
        # ========================================
        promotions_table = f"branch_{chain_code}_{branch_code}_promotions"
        
        # Create promotions table for this branch
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {promotions_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Promotion identification
                promotion_id TEXT NOT NULL,
                promotion_description TEXT NOT NULL,
                
                -- Dates and times
                promotion_update_date TIMESTAMP,
                promotion_start_date DATE,
                promotion_start_hour TIME,
                promotion_end_date DATE,
                promotion_end_hour TIME,
                
                -- Pricing information
                discounted_price REAL,
                discounted_price_per_unit REAL,
                discount_rate REAL,
                
                -- Rules and restrictions
                min_quantity INTEGER,
                max_quantity INTEGER,
                min_purchase_amount REAL,
                allow_multiple_discounts INTEGER,
                reward_type INTEGER,
                discount_type INTEGER,
                
                -- Additional info
                remarks TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create promotion items table for this branch
        promotion_items_table = f"branch_{chain_code}_{branch_code}_promotion_items"
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {promotion_items_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_id TEXT NOT NULL,
                item_code TEXT NOT NULL,
                is_gift_item INTEGER DEFAULT 0,
                item_type INTEGER DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (promotion_id) REFERENCES {promotions_table} (promotion_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Created branch tables: {table_name}, {promotions_table}, {promotion_items_table}")
        return table_name
    
    def add_food_chain(self, chain_code, chain_name, chain_url):
        """Add a food chain to the main index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO main_index (chain_code, chain_name, chain_url, last_update)
            VALUES (?, ?, ?, ?)
        ''', (chain_code, chain_name, chain_url, datetime.now().isoformat()))
        
        # Update total chains count
        cursor.execute('SELECT COUNT(*) FROM main_index')
        total_chains = cursor.fetchone()[0]
        
        cursor.execute('''
            UPDATE main_index_metadata 
            SET total_chains = ?, last_discovery_update = ?
            WHERE id = 1
        ''', (total_chains, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Create the chain table
        self.create_chain_table(chain_code, chain_name, chain_url)
        
        print(f"✅ Added food chain: {chain_name} ({chain_code})")
    
    def add_branch_to_chain(self, chain_code, branch_code, branch_name, price_file=None, promo_file=None):
        """Add a branch to a food chain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Add to chain's branches table
        table_name = f"chain_{chain_code}_branches"
        cursor.execute(f'''
            INSERT OR REPLACE INTO {table_name} (
                branch_code, branch_name, price_file_name, promo_file_name, 
                price_file_date, promo_file_date, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            branch_code, branch_name, price_file, promo_file,
            datetime.now().isoformat(), datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # Update branch count in metadata
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        total_branches = cursor.fetchone()[0]
        
        metadata_table = f"{table_name}_metadata"
        cursor.execute(f'''
            UPDATE {metadata_table} 
            SET total_branches = ?, last_update = ?
            WHERE id = 1
        ''', (total_branches, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Create the branch products table
        self.create_branch_table(chain_code, branch_code, branch_name, price_file, promo_file)
        
        print(f"✅ Added branch: {branch_name} ({branch_code}) to chain {chain_code}")
    
    def insert_branch_products(self, chain_code, branch_code, products_data):
        """Insert products into a branch table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"branch_{chain_code}_{branch_code}_products"
        metadata_table = f"{table_name}_metadata"
        
        # Clear existing products
        cursor.execute(f'DELETE FROM {table_name}')
        
        # Insert products
        for product in products_data:
            cursor.execute(f'''
                INSERT INTO {table_name} (
                    item_code, item_name, manufacturer_name, item_price,
                    unit_of_measure, quantity, price_update_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product.get('item_code', ''),
                product.get('item_name', ''),
                product.get('manufacturer_name', ''),
                float(product.get('item_price', 0)),
                product.get('unit_of_measure', ''),
                float(product.get('quantity', 0)) if product.get('quantity') else 0,
                product.get('price_update_date', '')
            ))
        
        # Update metadata
        cursor.execute(f'''
            UPDATE {metadata_table} 
            SET total_products = ?, last_update = ?
            WHERE id = 1
        ''', (len(products_data), datetime.now().isoformat()))
        
        # Also update total_promotions if the column exists
        try:
            cursor.execute(f'''
                UPDATE {metadata_table} 
                SET total_promotions = total_promotions
                WHERE id = 1
            ''')
        except sqlite3.Error:
            # Column might not exist, that's okay
            pass
        
        conn.commit()
        conn.close()
        
        print(f"✅ Inserted {len(products_data)} products into {table_name}")
        return len(products_data)
    
    def insert_branch_promotions(self, chain_code, branch_code, promotions_data):
        """Insert promotions into a branch table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        promotions_table = f"branch_{chain_code}_{branch_code}_promotions"
        promotion_items_table = f"branch_{chain_code}_{branch_code}_promotion_items"
        metadata_table = f"branch_{chain_code}_{branch_code}_products_metadata"
        
        # Clear existing promotions and items
        cursor.execute(f'DELETE FROM {promotion_items_table}')
        cursor.execute(f'DELETE FROM {promotions_table}')
        
        total_promotions = 0
        total_items = 0
        
        # Insert promotions
        for promotion in promotions_data:
            cursor.execute(f'''
                INSERT INTO {promotions_table} (
                    promotion_id, promotion_description, promotion_update_date,
                    promotion_start_date, promotion_start_hour, promotion_end_date, promotion_end_hour,
                    discounted_price, discounted_price_per_unit, discount_rate,
                    min_quantity, max_quantity, min_purchase_amount, allow_multiple_discounts,
                    reward_type, discount_type, remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                promotion.get('promotion_id', ''),
                promotion.get('promotion_description', ''),
                promotion.get('promotion_update_date', ''),
                promotion.get('promotion_start_date', ''),
                promotion.get('promotion_start_hour', ''),
                promotion.get('promotion_end_date', ''),
                promotion.get('promotion_end_hour', ''),
                float(promotion.get('discounted_price', 0) or 0),
                float(promotion.get('discounted_price_per_unit', 0) or 0),
                float(promotion.get('discount_rate', 0) or 0),
                int(float(promotion.get('min_quantity', 0) or 0)),
                int(float(promotion.get('max_quantity', 0) or 0)),
                float(promotion.get('min_purchase_amount', 0) or 0),
                int(float(promotion.get('allow_multiple_discounts', 0) or 0)),
                int(float(promotion.get('reward_type', 0) or 0)),
                int(float(promotion.get('discount_type', 0) or 0)),
                promotion.get('remarks', '')
            ))
            
            total_promotions += 1
            
            # Insert promotion items
            for item in promotion.get('items', []):
                cursor.execute(f'''
                    INSERT INTO {promotion_items_table} (
                        promotion_id, item_code, is_gift_item, item_type
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    promotion.get('promotion_id', ''),
                    item.get('item_code', ''),
                                    int(float(item.get('is_gift_item', 0) or 0)),
                int(float(item.get('item_type', 1) or 1))
                ))
                total_items += 1
        
        # Update metadata
        cursor.execute(f'''
            UPDATE {metadata_table} 
            SET total_promotions = ?, last_update = ?
            WHERE id = 1
        ''', (total_promotions, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Inserted {total_promotions} promotions and {total_items} items into {promotions_table}")
        return total_promotions
    
    def get_database_overview(self):
        """Get a complete overview of the hierarchical database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        overview = {
            "main_index": {},
            "food_chains": {},
            "total_tables": 0
        }
        
        # Get main index info
        try:
            cursor.execute('SELECT * FROM main_index_metadata WHERE id = 1')
            main_meta = cursor.fetchone()
            if main_meta:
                overview["main_index"] = {
                    "root_url": main_meta[1],
                    "total_chains": main_meta[2],
                    "last_discovery": main_meta[3]
                }
        except sqlite3.Error:
            pass
        
        # Get all food chains
        try:
            cursor.execute('SELECT chain_code, chain_name FROM main_index')
            chains = cursor.fetchall()
            
            for chain_code, chain_name in chains:
                chain_table = f"chain_{chain_code}_branches"
                metadata_table = f"{chain_table}_metadata"
                
                # Get chain metadata
                try:
                    cursor.execute(f'SELECT * FROM {metadata_table} WHERE id = 1')
                    chain_meta = cursor.fetchone()
                    
                    if chain_meta:
                        overview["food_chains"][chain_code] = {
                            "name": chain_meta[1],
                            "url": chain_meta[3],
                            "total_branches": chain_meta[4],
                            "last_update": chain_meta[5]
                        }
                except sqlite3.Error:
                    overview["food_chains"][chain_code] = {
                        "name": chain_name,
                        "error": "Metadata table not found"
                    }
        except sqlite3.Error:
            pass
        
        # Count total tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = cursor.fetchall()
        overview["total_tables"] = len(all_tables)
        
        conn.close()
        return overview

# Initialize the hierarchical database
db = HierarchicalFoodDatabase() 