import sqlite3
import os
import datetime

class FoodChainDatabase:
    def __init__(self, db_path="data/food_chains.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize database with optimized schema for product price lookups"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create metadata table to track food chains
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS food_chains_metadata (
                chain_code TEXT PRIMARY KEY,
                actual_chain_code TEXT,
                chain_name TEXT NOT NULL,
                chain_url TEXT NOT NULL,
                last_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create branches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_code TEXT NOT NULL,
                branch_code TEXT NOT NULL,
                branch_name TEXT NOT NULL,
                
                price_file_name TEXT,
                price_file_date TEXT,
                price_file_status TEXT DEFAULT 'pending',
                
                promo_file_name TEXT,
                promo_file_date TEXT,
                promo_file_status TEXT DEFAULT 'pending',
                
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (chain_code) REFERENCES food_chains_metadata(chain_code),
                UNIQUE(chain_code, branch_code)
            )
        ''')
        
        # Create products table - stores all products with prices per branch
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_code TEXT NOT NULL,
                branch_code TEXT NOT NULL,
                
                -- Product identification
                item_code TEXT NOT NULL,
                item_name TEXT NOT NULL,
                manufacturer_name TEXT,
                manufacturer_item_description TEXT,
                
                -- Pricing information
                item_price REAL NOT NULL,
                unit_of_measure_price REAL,
                unit_qty TEXT,
                quantity REAL,
                unit_of_measure TEXT,
                
                -- Product attributes
                is_weighted INTEGER DEFAULT 0,
                qty_in_package REAL,
                allow_discount INTEGER DEFAULT 1,
                item_status INTEGER DEFAULT 1,
                manufacture_country TEXT,
                
                -- Metadata
                price_update_date TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (chain_code, branch_code) REFERENCES branches(chain_code, branch_code),
                UNIQUE(chain_code, branch_code, item_code)
            )
        ''')
        
        # Create promotions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_code TEXT NOT NULL,
                branch_code TEXT NOT NULL,
                
                promotion_id TEXT NOT NULL,
                promotion_description TEXT NOT NULL,
                
                -- Date and time ranges
                promotion_start_date DATE,
                promotion_start_hour TIME,
                promotion_end_date DATE,
                promotion_end_hour TIME,
                
                -- Discount details
                reward_type INTEGER,
                discount_type INTEGER,
                discount_rate REAL,
                discounted_price REAL,
                discounted_price_per_mida REAL,
                
                -- Quantity rules
                min_qty INTEGER DEFAULT 1,
                max_qty INTEGER DEFAULT 0,
                min_purchase_amount REAL DEFAULT 0,
                
                -- Metadata  
                promotion_update_date TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (chain_code, branch_code) REFERENCES branches(chain_code, branch_code),
                UNIQUE(chain_code, branch_code, promotion_id)
            )
        ''')
        
        # Create promotion_items table - links promotions to products
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotion_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                is_gift_item INTEGER DEFAULT 0,
                item_type INTEGER DEFAULT 1,
                
                FOREIGN KEY (promotion_id) REFERENCES promotions(id),
                UNIQUE(promotion_id, item_code)
            )
        ''')
        
        # Create indexes for fast lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_item_code ON products(item_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_item_name ON products(item_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_branch ON products(chain_code, branch_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_promotions_dates ON promotions(promotion_start_date, promotion_end_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_promotion_items_code ON promotion_items(item_code)')
        
        conn.commit()
        conn.close()
        print(f"✅ Database initialized at: {self.db_path}")
    
    def add_food_chain(self, chain_code, chain_name, chain_url, actual_chain_code=None):
        """Add a food chain to the metadata table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO food_chains_metadata 
            (chain_code, actual_chain_code, chain_name, chain_url, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (chain_code, actual_chain_code, chain_name, chain_url, datetime.datetime.now()))
        
        conn.commit()
        conn.close()
        code_display = f"{chain_code}" + (f" -> {actual_chain_code}" if actual_chain_code else "")
        print(f"✅ Added food chain: {chain_name} ({code_display})")
    
    def update_actual_chain_code(self, placeholder_code, actual_chain_code):
        """Update the actual chain code for an existing food chain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE food_chains_metadata 
            SET actual_chain_code = ?, last_updated = ?
            WHERE chain_code = ? AND actual_chain_code IS NULL
        ''', (actual_chain_code, datetime.datetime.now(), placeholder_code))
        
        rows_updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_updated > 0:
            print(f"✅ Updated chain code: {placeholder_code} -> {actual_chain_code}")
        else:
            print(f"⚠️ No chain found to update with placeholder code: {placeholder_code}")
        
        return rows_updated > 0
    
    def insert_branches(self, chain_code, branches_data):
        """Insert branch information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for branch_code, branch_info in branches_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO branches 
                (chain_code, branch_code, branch_name, price_file_name, price_file_date, 
                 promo_file_name, promo_file_date, price_file_status, promo_file_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chain_code,
                branch_code,
                branch_info['name'],
                branch_info['price_file'],
                branch_info['price_date'],
                branch_info['promo_file'], 
                branch_info['promo_date'],
                'found' if branch_info['price_file'] else 'missing',
                'found' if branch_info['promo_file'] else 'missing'
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Inserted {len(branches_data)} branches for chain {chain_code}")
    
    def insert_products(self, chain_code, branch_code, products_data):
        """Insert parsed product data from PriceFull XML"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for product in products_data:
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (chain_code, branch_code, item_code, item_name, manufacturer_name,
                 manufacturer_item_description, item_price, unit_of_measure_price,
                 unit_qty, quantity, unit_of_measure, is_weighted, qty_in_package,
                 allow_discount, item_status, manufacture_country, price_update_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chain_code, branch_code, product['ItemCode'], product['ItemNm'],
                product['ManufacturerName'], product['ManufacturerItemDescription'],
                float(product['ItemPrice']), float(product['UnitOfMeasurePrice']),
                product['UnitQty'], float(product['Quantity']), product['UnitOfMeasure'],
                int(product['bIsWeighted']), float(product['QtyInPackage']),
                int(product['AllowDiscount']), int(product['ItemStatus']),
                product['ManufactureCountry'], product['PriceUpdateDate']
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Inserted {len(products_data)} products for branch {branch_code}")
    
    def insert_promotions(self, chain_code, branch_code, promotions_data):
        """Insert parsed promotion data from PromoFull XML"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for promo in promotions_data:
            # Insert promotion
            cursor.execute('''
                INSERT OR REPLACE INTO promotions 
                (chain_code, branch_code, promotion_id, promotion_description,
                 promotion_start_date, promotion_start_hour, promotion_end_date, promotion_end_hour,
                 reward_type, discount_type, discount_rate, discounted_price,
                 discounted_price_per_mida, min_qty, max_qty, min_purchase_amount,
                 promotion_update_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chain_code, branch_code, promo['PromotionId'], promo['PromotionDescription'],
                promo['PromotionStartDate'], promo['PromotionStartHour'],
                promo['PromotionEndDate'], promo['PromotionEndHour'],
                int(promo['RewardType']), int(promo['DiscountType']),
                float(promo['DiscountRate']), float(promo['DiscountedPrice']),
                float(promo['DiscountedPricePerMida']), int(promo['MinQty']),
                int(promo['MaxQty']), float(promo['MinPurchaseAmnt']),
                promo['PromotionUpdateDate']
            ))
            
            promotion_db_id = cursor.lastrowid
            
            # Insert promotion items
            for item in promo['PromotionItems']:
                cursor.execute('''
                    INSERT OR REPLACE INTO promotion_items
                    (promotion_id, item_code, is_gift_item, item_type)
                    VALUES (?, ?, ?, ?)
                ''', (promotion_db_id, item['ItemCode'], int(item['IsGiftItem']), int(item['ItemType'])))
        
        conn.commit()
        conn.close()
        print(f"✅ Inserted {len(promotions_data)} promotions for branch {branch_code}")
    
    def search_products(self, search_term, chain_code=None):
        """Search for products by name or code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT DISTINCT p.item_code, p.item_name, p.chain_code, 
                   COUNT(DISTINCT p.branch_code) as branch_count,
                   MIN(p.item_price) as min_price,
                   MAX(p.item_price) as max_price
            FROM products p
            WHERE (p.item_name LIKE ? OR p.item_code LIKE ?)
        '''
        params = [f'%{search_term}%', f'%{search_term}%']
        
        if chain_code:
            query += ' AND p.chain_code = ?'
            params.append(chain_code)
        
        query += ' GROUP BY p.item_code, p.item_name, p.chain_code ORDER BY p.item_name'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [{'item_code': r[0], 'item_name': r[1], 'chain_code': r[2], 
                'branch_count': r[3], 'min_price': r[4], 'max_price': r[5]} for r in results]
    
    def get_product_prices(self, item_codes, chain_code):
        """Get prices for specific products across all branches"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in item_codes])
        query = f'''
            SELECT p.item_code, p.item_name, p.branch_code, b.branch_name,
                   p.item_price, p.unit_of_measure_price, p.price_update_date
            FROM products p
            JOIN branches b ON p.chain_code = b.chain_code AND p.branch_code = b.branch_code
            WHERE p.item_code IN ({placeholders}) AND p.chain_code = ?
            ORDER BY p.item_code, p.item_price
        '''
        
        cursor.execute(query, item_codes + [chain_code])
        results = cursor.fetchall()
        conn.close()
        
        return [{'item_code': r[0], 'item_name': r[1], 'branch_code': r[2], 
                'branch_name': r[3], 'price': r[4], 'unit_price': r[5], 
                'updated': r[6]} for r in results]
    
    def get_database_status(self):
        """Get comprehensive database status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get chain info
        cursor.execute('SELECT * FROM food_chains_metadata')
        chains = cursor.fetchall()
        
        status = {"database_path": self.db_path, "chains": {}}
        
        for chain in chains:
            chain_code, actual_chain_code, chain_name, chain_url, last_updated, created_at = chain
            
            # Branch statistics
            cursor.execute('SELECT COUNT(*) FROM branches WHERE chain_code = ?', (chain_code,))
            total_branches = cursor.fetchone()[0]
            
            # Product statistics
            cursor.execute('SELECT COUNT(*) FROM products WHERE chain_code = ?', (chain_code,))
            total_products = cursor.fetchone()[0]
            
            # Promotion statistics
            cursor.execute('SELECT COUNT(*) FROM promotions WHERE chain_code = ?', (chain_code,))
            total_promotions = cursor.fetchone()[0]
            
            status["chains"][chain_code] = {
                "name": chain_name,
                "url": chain_url,
                "actual_chain_code": actual_chain_code,
                "branches": total_branches,
                "products": total_products,
                "promotions": total_promotions,
                "last_updated": last_updated
            }
        
        conn.close()
        return status

# Example usage
if __name__ == "__main__":
    print("🚀 Initializing Optimized Food Chain Database...")
    
    db = FoodChainDatabase()
    
    # Add KingStore chain with both placeholder and actual codes
    db.add_food_chain("CHAIN_001", "KingStore", "https://kingstore.binaprojects.com/Main.aspx", "7290058108879")
    
    # Show status
    status = db.get_database_status()
    print(f"\n📊 Database Status:")
    for chain_code, info in status["chains"].items():
        print(f"  Chain {chain_code}: {info['name']}")
        print(f"    Branches: {info['branches']}")
        print(f"    Products: {info['products']}")
        print(f"    Promotions: {info['promotions']}")
    
    print(f"\n✅ Optimized database ready for product price comparisons!")
    print(f"📁 Database location: {db.db_path}") 