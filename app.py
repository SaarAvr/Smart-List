from flask import Flask, jsonify
from selenium.webdriver.support import expected_conditions as EC
from flask import jsonify
import zipfile
import datetime
import os
import json
import gzip
import io
import time
from database_setup import FoodChainDatabase
from database_hierarchical import HierarchicalFoodDatabase

app = Flask(__name__)

# Configure Flask to use compact JSON (no pretty printing)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Global database instance
db = FoodChainDatabase()
hierarchical_db = HierarchicalFoodDatabase()
data_directory = "data"

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    if not os.path.exists(data_directory):
        os.makedirs(data_directory)
        log_message(f"📁 Created data directory: {data_directory}")

def get_all_food_chains():
    """
    Extract all food chains from the government website
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        log_message("📡 Scanning all food chains from government website...")
        driver.get("https://www.gov.il/he/pages/cpfta_prices_regulations")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        if not rows:
            log_message("❌ ERROR: No chain rows found")
            driver.quit()
            return []

        log_message(f"✅ Found {len(rows)} food chain rows on government site")
        
        food_chains = []
        
        for i, row in enumerate(rows):
            try:
                # Get the link URL
                link = row.find_element(By.TAG_NAME, "a")
                chain_url = link.get_attribute("href")
                link_text = link.text.strip()
                
                # Get all cells in the row
                row_cells = row.find_elements(By.TAG_NAME, "td")
                if len(row_cells) >= 3:
                    # Extract chain name from the LEFTMOST column (Cell 0)
                    chain_name = row_cells[0].text.strip()
                    
                    # Basic validation - just check link text and ensure we have name and URL
                    if "לצפי" not in link_text:
                        log_message(f"⏭️  Skipping row {i+1}: Link text doesn't contain 'לצפי' (got: '{link_text}')")
                        continue
                    
                    # Sequential chain code for all discovered chains
                    chain_code = f"CHAIN_{len(food_chains)+1:03d}"
                    
                    if chain_name and chain_url:
                        food_chains.append({
                            "code": chain_code,
                            "name": chain_name,
                            "url": chain_url
                        })
                        log_message(f"🏢 Chain {len(food_chains)}: {chain_name}")
                        
            except Exception as e:
                log_message(f"⚠️  Warning: Could not extract chain {i+1}: {str(e)}")
                continue
        
        log_message(f"📊 Successfully extracted {len(food_chains)} food chains")
        return food_chains
        
    except Exception as e:
        log_message(f"❌ ERROR getting food chains: {str(e)}")
        return []
    finally:
        driver.quit()


def get_food_chain_and_branches():
    """Get food chain metadata and all branches from the dropdown"""
    log_message("🚀 Starting food chain and branch discovery...")
    
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        log_message("📡 Navigating to government website...")
        driver.get("https://www.gov.il/he/pages/cpfta_prices_regulations")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        if not rows:
            log_message("❌ ERROR: No chain rows found")
            driver.quit()
            return {}, "", None

        log_message(f"✅ Found {len(rows)} food chain rows on government site")
        
        # Get first food chain information
        first_row = rows[0]
        first_link = first_row.find_element(By.TAG_NAME, "a")
        chain_url = first_link.get_attribute("href")
        
        # Get actual food chain name from the leftmost column (not the link text)
        row_cells = first_row.find_elements(By.TAG_NAME, "td")
        chain_name_element = row_cells[0].text.strip() if row_cells else "KingStore"
        
        # Extract chain code from URL or other means (KingStore specific)
        # For KingStore, we know the chain code from the file patterns
        chain_code = "7290058108879"  # This will be extracted dynamically later
        
        chain_info = {
            "code": chain_code,
            "name": chain_name_element or "KingStore",  # Fallback to KingStore
            "url": chain_url
        }
        
        log_message(f"🏢 Food Chain: {chain_info['name']} (Code: {chain_info['code']})")
        log_message(f"🔗 Chain URL: {chain_url}")

        log_message("📊 Loading chain page and waiting for branch dropdown...")
        driver.get(chain_url)
        
        # Wait for the warehouse dropdown to be populated
        log_message("⏳ Waiting for warehouse dropdown to load...")
        for attempt in range(10):
            try:
                warehouse_select = driver.find_element(By.ID, "wStore")
                options_list = warehouse_select.find_elements(By.TAG_NAME, "option")
                log_message(f"🔄 Attempt {attempt + 1}: Found {len(options_list)} options in dropdown")
                if len(options_list) > 1:
                    break
                time.sleep(1)
            except Exception as e:
                log_message(f"⚠️  Attempt {attempt + 1} failed: {str(e)}")
                time.sleep(1)

        log_message("🏪 Extracting branch information from dropdown...")
        branch_dict = {}
        for option in options_list:
            code = option.get_attribute("value").strip()
            name = option.text.strip()
            if code and name and code != "0":
                # Remove the code prefix from the name (e.g., "1 אום אלפחם" -> "אום אלפחם")
                clean_name = name.split(' ', 1)[1] if ' ' in name else name
                branch_dict[code] = clean_name
                log_message(f"   ✅ Found branch: {clean_name} (Code: {code})")

        driver.quit()
        log_message(f"🎉 SUCCESS: Found {len(branch_dict)} branches from {chain_info['name']}!")
        return branch_dict, chain_url, chain_info
        
    except Exception as e:
        driver.quit()
        log_message(f"❌ ERROR during food chain discovery: {str(e)}")
        return {}, "", None

def get_files_from_table(chain_url):
    """Get latest files for each branch from the data table - DEBUG VERSION"""
    log_message("🔍 Starting file discovery from data table...")
    
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
    import re

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        log_message(f"📡 Navigating to chain URL: {chain_url}")
        driver.get(chain_url)
        
        # Wait for the file table to be populated
        WebDriverWait(driver, 30).until(
            lambda d: any(len(row.find_elements(By.TAG_NAME, "td")) > 0 for row in d.find_elements(By.CSS_SELECTOR, "table#myTable tr"))
        )
        chain_rows = driver.find_elements(By.CSS_SELECTOR, "table#myTable tr")
        log_message(f"✅ Found {len(chain_rows)} file entries in table")

        branch_files = {}
        
        # Debug: Check first few rows to see the data structure
        log_message("🔍 DEBUG: Examining first 5 rows of file table...")
        for i, row in enumerate(chain_rows[:5]):
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 2:
                file_name = cells[0].text.strip()
                branch_code_full = cells[1].text.strip()
                branch_code_numeric = branch_code_full.split(' ', 1)[0] if ' ' in branch_code_full else branch_code_full
                log_message(f"   Row {i+1}: FileName='{file_name}' | Full='{branch_code_full}' | Numeric='{branch_code_numeric}'")

        for row in chain_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 5:
                continue
            file_name = cells[0].text.strip()
            branch_code_full = cells[1].text.strip()
            
            # Skip empty or invalid entries
            if not file_name or not branch_code_full:
                continue
            
            # Extract just the numeric code from "339 יפו תלאביב מכללה" -> "339"
            branch_code = branch_code_full.split(' ', 1)[0] if ' ' in branch_code_full else branch_code_full
            
            # Debug specific branches that are missing
            if branch_code in ['337', '50']:
                log_message(f"🔍 DEBUG: Processing missing branch {branch_code} | File: {file_name}")
                
            # Extract date from end of filename: PriceFull7290058108879-001-202507271024.gz -> 202507271024
            match = re.search(r'-(\d{12})\.gz$', file_name)
            file_date = match.group(1) if match else ""
            
            if "PriceFull" in file_name:
                file_type = "PriceFull"
            elif "PromoFull" in file_name:
                file_type = "PromoFull"
            else:
                if branch_code in ['337', '50']:
                    log_message(f"🔍 DEBUG: Branch {branch_code} file skipped - not PriceFull/PromoFull: {file_name}")
                continue

            key = f"{branch_code}"
            if key not in branch_files:
                branch_files[key] = {"PriceFull": ("", ""), "PromoFull": ("", "")}
            
            if file_type == "PriceFull" and file_date > branch_files[key]["PriceFull"][1]:
                branch_files[key]["PriceFull"] = (file_name, file_date)
                log_message(f"   📄 Updated PriceFull for branch {branch_code} (from '{branch_code_full}'): {file_name}")
            if file_type == "PromoFull" and file_date > branch_files[key]["PromoFull"][1]:
                branch_files[key]["PromoFull"] = (file_name, file_date)
                log_message(f"   🎯 Updated PromoFull for branch {branch_code} (from '{branch_code_full}'): {file_name}")

        driver.quit()
        log_message(f"📁 Found files for {len(branch_files)} branches")
        
        # Debug: Show the extracted branch codes we're using as keys
        branch_codes = list(branch_files.keys())[:10]  # First 10 for brevity
        log_message(f"🔍 DEBUG: File table branch codes (first 10): {branch_codes}")
        
        # Debug: Check specifically for missing branches 337 and 50
        missing_branches = []
        for check_branch in ['337', '50']:
            if check_branch not in branch_files:
                missing_branches.append(check_branch)
        
        if missing_branches:
            log_message(f"🔍 DEBUG: Branches completely missing from file table: {missing_branches}")
        
        return branch_files
        
    except Exception as e:
        driver.quit()
        log_message(f"❌ ERROR during file discovery: {str(e)}")
        return {}

def discover_and_store_food_chain_data():
    """Main function to discover food chain, branches, and store in database"""
    global db
    
    log_message("🚀 Starting comprehensive food chain discovery and database population...")
    
    # Step 1: Get ALL food chains from government website
    log_message("📊 Phase 1: Discovering all food chains...")
    all_food_chains = get_all_food_chains()
    
    if not all_food_chains:
        log_message("❌ Failed to discover any food chains")
        return
    
    # Step 2: Store all food chain metadata in database
    log_message(f"💾 Storing metadata for {len(all_food_chains)} food chains...")
    for chain in all_food_chains:
        try:
            db.add_food_chain(chain['code'], chain['name'], chain['url'])
            log_message(f"   ✅ Stored: {chain['name']}")
        except Exception as e:
            log_message(f"   ⚠️  Warning: Failed to store {chain['name']}: {str(e)}")
    
    log_message("🎉 All food chains stored in database!")
    
    # Step 3: Get detailed branch data for KingStore only (to avoid processing all chains)
    log_message("📊 Phase 2: Getting detailed branch data for KingStore...")
    branch_dict, chain_url, chain_info = get_food_chain_and_branches()
    
    if not branch_dict or not chain_info:
        log_message("❌ Failed to get detailed KingStore data, but all chains are stored")
        return
    
    # Step 4: Find KingStore's placeholder code and update it with actual chain code
    log_message(f"💾 Updating KingStore placeholder with actual chain code...")
    
    # Find KingStore in the stored chains (should be CHAIN_001 since it's first)
    kingstore_placeholder = None
    for chain in all_food_chains:
        if "קינג סטור" in chain['name'] or "kingstore" in chain['url'].lower():
            kingstore_placeholder = chain['code']
            break
    
    if kingstore_placeholder:
        # Update the existing entry with actual chain code
        success = db.update_actual_chain_code(kingstore_placeholder, chain_info['code'])
        if success:
            log_message(f"✅ Updated {kingstore_placeholder} with actual code: {chain_info['code']}")
        else:
            log_message(f"⚠️ Failed to update KingStore placeholder code")
    else:
        log_message(f"⚠️ Could not find KingStore placeholder in stored chains")
    
    # Step 5: Get file information for branches
    branch_files = get_files_from_table(chain_url)
    
    # Step 6: Combine branch data with file information
    log_message("🔧 Preparing branch data for database...")
    branches_for_db = {}
    
    for branch_code, branch_name in branch_dict.items():
        files_info = branch_files.get(branch_code, {"PriceFull": ("", ""), "PromoFull": ("", "")})
        branches_for_db[branch_code] = {
            "name": branch_name,
            "price_file": files_info["PriceFull"][0],
            "price_date": files_info["PriceFull"][1],
            "promo_file": files_info["PromoFull"][0],
            "promo_date": files_info["PromoFull"][1]
        }
        
        # Log file status for each branch
        price_status = "✅" if files_info["PriceFull"][0] else "❌"
        promo_status = "✅" if files_info["PromoFull"][0] else "❌"
        log_message(f"   🏪 {branch_code}: {branch_name} | Price: {price_status} | Promo: {promo_status}")

    # Step 7: Store all branch data in database (using placeholder code for foreign key consistency)
    log_message(f"💾 Storing {len(branches_for_db)} branches in database...")
    chain_code_for_branches = kingstore_placeholder if kingstore_placeholder else chain_info['code']
    db.insert_branches(chain_code_for_branches, branches_for_db)
    
    # Step 8: Show database status
    status = db.get_database_status()
    log_message(f"🎉 SUCCESS: Database populated!")
    for chain_code, info in status["chains"].items():
        log_message(f"  📊 Chain {chain_code}: {info['name']} - {info['branches']} branches stored")
    
    log_message(f"📁 Database location: {db.db_path}")

@app.route('/get-branches')
def get_branches():
    """Return the list of all branches from database"""
    log_message("🔥 NEW REQUEST: /get-branches")
    
    try:
        # Get branches from database
        conn = db.db.connect() if hasattr(db, 'db') else None
        if not conn:
            import sqlite3
            conn = sqlite3.connect(db.db_path)
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.branch_code, b.branch_name, b.price_file_name, b.price_file_date,
                   b.promo_file_name, b.promo_file_date, b.price_file_status, b.promo_file_status
            FROM branches b
            ORDER BY CAST(b.branch_code AS INTEGER)
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            log_message("❌ No branch data available in database!")
            return jsonify({"error": "No branch data available. Server may still be initializing."})
        
        # Convert to list of objects
        branches_list = [{
            "code": row[0],
            "name": row[1],
            "price_file": row[2] or "",
            "price_date": row[3] or "",
            "promo_file": row[4] or "",
            "promo_date": row[5] or "",
            "price_status": row[6],
            "promo_status": row[7]
        } for row in rows]
    
        log_message(f"📤 Returning {len(branches_list)} branches from database (sorted by code)")
        
        import json
        from flask import Response
        
        # Custom formatting: compact but with each branch object on its own line
        json_str = '{\n  "branches": [\n'
        for i, branch in enumerate(branches_list):
            comma = "," if i < len(branches_list) - 1 else ""
            json_str += f'    {json.dumps(branch, ensure_ascii=False)}{comma}\n'
        json_str += f'  ],\n  "total_branches": {len(branches_list)}\n}}'
        
        return Response(json_str, mimetype='application/json')
        
    except Exception as e:
        log_message(f"❌ ERROR serving branches from database: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"})

@app.route('/food-chains')
def get_food_chains():
    """Return all food chains from database"""
    log_message("🔥 NEW REQUEST: /food-chains")
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chain_code, chain_name, chain_url, created_at 
            FROM food_chains_metadata 
            ORDER BY chain_name
        """)
        
        chains = []
        for row in cursor.fetchall():
            chains.append({
                "code": row[0],
                "name": row[1], 
                "url": row[2],
                "created_at": row[3]
            })
        
        conn.close()
        log_message(f"📊 Retrieved {len(chains)} food chains")
        return jsonify({
            "total_chains": len(chains),
            "chains": chains
        })
        
    except Exception as e:
        log_message(f"❌ ERROR getting food chains: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/status')
def status():
    """Show server status and database info"""
    try:
        db_status = db.get_database_status()
        return jsonify({
            "status": "running",
            "database": db_status,
            "data_directory": data_directory
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "data_directory": data_directory
        })

# ============================================================================
# HIERARCHICAL DATABASE ENDPOINTS FOR HTML VIEWER
# ============================================================================

@app.route('/hierarchical-overview')
def get_hierarchical_overview():
    """Get complete hierarchical database overview"""
    try:
        overview = hierarchical_db.get_database_overview()
        return jsonify(overview)
    except Exception as e:
        return jsonify({
            "error": f"Failed to get database overview: {str(e)}"
        })

@app.route('/hierarchical-chain/<chain_code>')
def get_chain_branches(chain_code):
    """Get all branches for a specific chain"""
    try:
        import sqlite3
        conn = sqlite3.connect(hierarchical_db.db_path)
        cursor = conn.cursor()
        
        # Get branches for this chain
        branches_table = f"chain_{chain_code}_branches"
        cursor.execute(f'''
            SELECT branch_code, branch_name, price_file_name, promo_file_name, 
                   price_file_date, promo_file_date, address, coordinates
            FROM {branches_table} 
            ORDER BY CAST(branch_code AS INTEGER)
        ''')
        
        branches_raw = cursor.fetchall()
        branches = []
        
        for row in branches_raw:
            branches.append({
                "branch_code": row[0],
                "branch_name": row[1],
                "price_file_name": row[2],
                "promo_file_name": row[3],
                "price_file_date": row[4],
                "promo_file_date": row[5],
                "address": row[6],
                "coordinates": row[7]
            })
        
        conn.close()
        
        return jsonify({
            "chain_code": chain_code,
            "branches": branches
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get branches for {chain_code}: {str(e)}"
        })

@app.route('/hierarchical-viewer')
def serve_hierarchical_viewer():
    """Serve the hierarchical database viewer HTML page"""
    try:
        with open('hierarchical_viewer.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except Exception as e:
        return f"Error loading viewer: {str(e)}", 500

@app.route('/hierarchical-branch/<chain_code>/<branch_code>')
def get_branch_products(chain_code, branch_code):
    """Get products for a specific branch"""
    try:
        import sqlite3
        conn = sqlite3.connect(hierarchical_db.db_path)
        cursor = conn.cursor()
        
        # Get branch metadata
        products_table = f"branch_{chain_code}_{branch_code}_products"
        metadata_table = f"{products_table}_metadata"
        
        cursor.execute(f'SELECT * FROM {metadata_table} WHERE id = 1')
        metadata_raw = cursor.fetchone()
        
        metadata = {}
        if metadata_raw:
            metadata = {
                "chain_code": metadata_raw[1],
                "branch_code": metadata_raw[2],
                "branch_name": metadata_raw[3],
                "latest_price_file": metadata_raw[4],
                "latest_promo_file": metadata_raw[5],
                "total_products": metadata_raw[6],
                "last_update": metadata_raw[7],
                "total_promotions": metadata_raw[9] if len(metadata_raw) > 9 else 0
            }
        
        # Get top 50 products by price
        cursor.execute(f'''
            SELECT item_code, item_name, manufacturer_name, item_price, 
                   unit_of_measure, quantity, price_update_date
            FROM {products_table} 
            ORDER BY CAST(item_price AS REAL) DESC 
            LIMIT 50
        ''')
        
        products_raw = cursor.fetchall()
        products = []
        
        for row in products_raw:
            products.append({
                "item_code": row[0],
                "item_name": row[1],
                "manufacturer_name": row[2],
                "item_price": row[3],
                "unit_of_measure": row[4],
                "quantity": row[5],
                "price_update_date": row[6]
            })
        
        # Get top 50 promotions by discounted price
        promotions_table = f"branch_{chain_code}_{branch_code}_promotions"
        promotion_items_table = f"branch_{chain_code}_{branch_code}_promotion_items"
        promotions = []
        
        try:
            cursor.execute(f'''
                SELECT p.promotion_id, p.promotion_description, p.discounted_price, 
                       p.min_quantity, p.promotion_end_date, p.promotion_start_date,
                       p.max_quantity, p.discounted_price_per_unit
                FROM {promotions_table} p
                ORDER BY CAST(p.discounted_price AS REAL) DESC 
                LIMIT 50
            ''')
            
            promotions_raw = cursor.fetchall()
            
            for row in promotions_raw:
                promotion_id = row[0]
                
                # Get items for this promotion
                cursor.execute(f'''
                    SELECT item_code FROM {promotion_items_table}
                    WHERE promotion_id = ?
                ''', (promotion_id,))
                
                items_raw = cursor.fetchall()
                item_codes = [item[0] for item in items_raw]
                
                promotions.append({
                    "promotion_id": promotion_id,
                    "promotion_description": row[1],
                    "discounted_price": row[2],
                    "min_quantity": row[3],
                    "promotion_end_date": row[4],
                    "promotion_start_date": row[5],
                    "max_quantity": row[6],
                    "discounted_price_per_unit": row[7],
                    "item_codes": item_codes,
                    "item_count": len(item_codes)
                })
        except sqlite3.Error as e:
            # Promotions table might not exist yet
            print(f"Promotions query error: {str(e)}")
            pass
        
        conn.close()
        
        return jsonify({
            "chain_code": chain_code,
            "branch_code": branch_code,
            "metadata": metadata,
            "products": products,
            "promotions": promotions
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get products for branch {branch_code}: {str(e)}"
        })

# ============================================================================
# PHASE 1: DOWNLOAD, DECOMPRESS, AND PARSE BRANCH DATA
# ============================================================================

import requests
import gzip
import xml.etree.ElementTree as ET
import os
import sqlite3

def download_branch_files(branch_code, price_filename, promo_filename):
    """Download actual files from KingStore website"""
    print(f"📥 REAL DOWNLOAD: Starting for branch {branch_code}")
    print(f"📄 Target files: {price_filename}, {promo_filename}")
    
    downloaded_files = {}
    driver = None
    
    try:
        # Set up Selenium WebDriver
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        import os
        import time
        
        # Configure Chrome options for download with anti-bot measures
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless Chrome
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Real user agent to avoid bot detection
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"--user-agent={user_agent}")
        
        # ========================================
        # DOWNLOAD DIRECTORY CONFIGURATION
        # ========================================
        # This is the main download directory for all food chain files
        # Change this path when moving the backend to production
        DOWNLOAD_BASE_DIR = "downloads"  # TODO: Make this configurable via environment variable
        
        download_dir = os.path.abspath(DOWNLOAD_BASE_DIR)
        os.makedirs(download_dir, exist_ok=True)
        print(f"📁 Download directory: {download_dir}")
        
        # Clean up old duplicate files before downloading
        print("🗑️ Cleaning up old duplicate files...")
        import glob
        duplicate_files = glob.glob(os.path.join(download_dir, "*(*)*"))
        for file_path in duplicate_files:
            os.remove(file_path)
        if duplicate_files:
            print(f"✅ Removed {len(duplicate_files)} duplicate files")
        
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove webdriver property to avoid detection
        driver.execute_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
        
        print("🌐 Navigating to KingStore page...")
        driver.get("https://kingstore.binaprojects.com/Main.aspx")
        
        # Wait for the page to load and find the file table
        WebDriverWait(driver, 30).until(
            lambda d: any(len(row.find_elements(By.TAG_NAME, "td")) > 0 
                         for row in d.find_elements(By.CSS_SELECTOR, "table tr"))
        )
        
        print(f"🔍 Looking for files: {price_filename}, {promo_filename}")
        
        # Find all table rows
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        files_downloaded = 0
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 5:
                continue
                
            file_name = cells[0].text.strip()
            row_branch_code = cells[1].text.strip()
            
            # Check if this row matches our target branch and file patterns
            # Branch codes are like "1 אום אלפחם", so check if it starts with our branch_code
            branch_matches = row_branch_code.startswith(branch_code + ' ') or row_branch_code == branch_code
            
            # Check for file pattern matches (handle both Price/PriceFull and Promo/PromoFull)
            is_price_file = ('Price' in file_name and branch_code in file_name and 
                           (file_name == price_filename or 
                            file_name.replace('PriceFull', 'Price') == price_filename.replace('PriceFull', 'Price')))
            is_promo_file = ('Promo' in file_name and branch_code in file_name and
                           (file_name == promo_filename or 
                            file_name.replace('PromoFull', 'Promo') == promo_filename.replace('PromoFull', 'Promo')))
            
            if branch_matches and (is_price_file or is_promo_file):
                
                print(f"📥 Found target file: {file_name}")
                
                # Look for download button in the last cell (cell 5)
                if len(cells) >= 6:  # Make sure we have enough cells
                    download_buttons = cells[5].find_elements(By.TAG_NAME, "button")
                    for button in download_buttons:
                        print(f"🖱️ Clicking download button for {file_name}")
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(3)  # Wait for download to start
                        files_downloaded += 1
                        
                        # Store the expected downloaded file path 
                        # Note: Use the original expected filename, not the actual file_name from the table
                        if is_price_file:
                            # Map to the expected PriceFull filename, not the Price filename from table
                            expected_price_file = price_filename if price_filename else file_name
                            downloaded_files['price_file'] = os.path.join(download_dir, expected_price_file)
                        elif is_promo_file:
                            expected_promo_file = promo_filename if promo_filename else file_name
                            downloaded_files['promo_file'] = os.path.join(download_dir, expected_promo_file)
                        break
        
        driver.quit()
        
        if files_downloaded > 0:
            print(f"✅ Successfully initiated {files_downloaded} file downloads")
            # Wait a bit more for files to finish downloading
            time.sleep(5)
        else:
            print("❌ No matching files found for download")
            
        return downloaded_files
        
    except Exception as e:
        print(f"❌ Error downloading files: {str(e)}")
        if driver:
            driver.quit()
        return None

def decompress_gz_file(filepath):
    """Read XML file (handles .gz, .zip, and regular .xml files)"""
    print(f"📦 Reading file: {filepath}")
    
    try:
        # Check file signature to determine actual format
        with open(filepath, 'rb') as f:
            signature = f.read(2)
        
        if signature == b'PK':
            # ZIP file (common for government data files)
            print("🗜️ Detected ZIP file, extracting...")
            import zipfile
            with zipfile.ZipFile(filepath, 'r') as zip_file:
                # Get the first XML file in the zip
                xml_files = [name for name in zip_file.namelist() if name.endswith('.xml')]
                if xml_files:
                    with zip_file.open(xml_files[0]) as xml_file:
                        xml_content = xml_file.read().decode('utf-8')
                else:
                    raise Exception("No XML file found in ZIP archive")
                    
        elif signature == b'\x1f\x8b':
            # Gzip file
            print("🗜️ Detected gzip file, decompressing...")
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                xml_content = f.read()
        else:
            # Regular XML file
            print("📄 Regular XML file, reading directly...")
            with open(filepath, 'r', encoding='utf-8') as f:
                xml_content = f.read()
                
        print(f"✅ File read successfully, XML size: {len(xml_content)} characters")
        return xml_content
    except Exception as e:
        print(f"❌ Error reading {filepath}: {str(e)}")
        return None

def parse_price_xml(xml_content):
    """Parse PriceFull XML and return list of products"""
    print("🔍 Parsing PriceFull XML...")
    
    try:
        root = ET.fromstring(xml_content)
        products = []
        
        # Extract metadata
        chain_id = root.find('ChainId').text if root.find('ChainId') is not None else ""
        store_id = root.find('StoreId').text if root.find('StoreId') is not None else ""
        
        # Parse items
        items = root.find('Items')
        if items is not None:
            for item in items.findall('Item'):
                product = {
                    'chain_id': chain_id,
                    'store_id': store_id,
                    'item_code': get_xml_text(item, 'ItemCode'),
                    'item_name': get_xml_text(item, 'ItemNm'),
                    'manufacturer_name': get_xml_text(item, 'ManufacturerName'),
                    'manufacturer_item_description': get_xml_text(item, 'ManufacturerItemDescription'),
                    'unit_qty': get_xml_text(item, 'UnitQty'),
                    'quantity': get_xml_text(item, 'Quantity'),
                    'unit_of_measure': get_xml_text(item, 'UnitOfMeasure'),
                    'is_weighted': get_xml_text(item, 'bIsWeighted'),
                    'qty_in_package': get_xml_text(item, 'QtyInPackage'),
                    'item_price': get_xml_text(item, 'ItemPrice'),
                    'unit_of_measure_price': get_xml_text(item, 'UnitOfMeasurePrice'),
                    'allow_discount': get_xml_text(item, 'AllowDiscount'),
                    'item_status': get_xml_text(item, 'ItemStatus'),
                    'manufacture_country': get_xml_text(item, 'ManufactureCountry'),
                    'price_update_date': get_xml_text(item, 'PriceUpdateDate')
                }
                products.append(product)
        
        print(f"✅ Parsed {len(products)} products from PriceFull XML")
        return products
        
    except Exception as e:
        print(f"❌ Error parsing PriceFull XML: {str(e)}")
        return []

def parse_promo_xml(xml_content):
    """Parse PromoFull XML and return list of promotions"""
    print("🎯 Parsing PromoFull XML...")
    
    try:
        root = ET.fromstring(xml_content)
        promotions = []
        
        # Extract metadata
        chain_id = root.find('ChainId').text if root.find('ChainId') is not None else ""
        store_id = root.find('StoreId').text if root.find('StoreId') is not None else ""
        
        # Parse promotions
        promos = root.find('Promotions')
        if promos is not None:
            for promo in promos.findall('Promotion'):
                promotion = {
                    'chain_id': chain_id,
                    'store_id': store_id,
                    'promotion_id': get_xml_text(promo, 'PromotionId'),
                    'promotion_description': get_xml_text(promo, 'PromotionDescription'),
                    'promotion_update_date': get_xml_text(promo, 'PromotionUpdateDate'),
                    'promotion_start_date': get_xml_text(promo, 'PromotionStartDate'),
                    'promotion_start_hour': get_xml_text(promo, 'PromotionStartHour'),
                    'promotion_end_date': get_xml_text(promo, 'PromotionEndDate'),
                    'promotion_end_hour': get_xml_text(promo, 'PromotionEndHour'),
                    'discounted_price': get_xml_text(promo, 'DiscountedPrice'),
                    'discounted_price_per_unit': get_xml_text(promo, 'DiscountedPricePerMida'),
                    'discount_rate': get_xml_text(promo, 'DiscountRate'),
                    'min_quantity': get_xml_text(promo, 'MinQty'),
                    'max_quantity': get_xml_text(promo, 'MaxQty'),
                    'min_purchase_amount': get_xml_text(promo, 'MinPurchaseAmnt'),
                    'allow_multiple_discounts': get_xml_text(promo, 'AllowMultipleDiscounts'),
                    'reward_type': get_xml_text(promo, 'RewardType'),
                    'discount_type': get_xml_text(promo, 'DiscountType'),
                    'remarks': get_xml_text(promo, 'Remarks'),
                    'items': []
                }
                
                # Parse promotion items
                promo_items = promo.find('PromotionItems')
                if promo_items is not None:
                    for item in promo_items.findall('Item'):
                        promotion['items'].append({
                            'item_code': get_xml_text(item, 'ItemCode'),
                            'is_gift_item': get_xml_text(item, 'IsGiftItem'),
                            'item_type': get_xml_text(item, 'ItemType')
                        })
                
                promotions.append(promotion)
        
        print(f"✅ Parsed {len(promotions)} promotions from PromoFull XML")
        return promotions
        
    except Exception as e:
        print(f"❌ Error parsing PromoFull XML: {str(e)}")
        return []

def get_xml_text(element, tag_name):
    """Helper function to safely get text from XML element"""
    child = element.find(tag_name)
    return child.text if child is not None else ""

@app.route('/process-branch/<branch_code>')
def process_branch(branch_code):
    """Download, decompress, and parse data for a specific branch"""
    log_message(f"🚀 NEW REQUEST: /process-branch/{branch_code}")
    
    try:
        # Get branch info from database
        conn = db.db.connect() if hasattr(db, 'db') else None
        if not conn:
            import sqlite3
            conn = sqlite3.connect(db.db_path)
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT branch_code, branch_name, price_file_name, promo_file_name
            FROM branches 
            WHERE branch_code = ?
        ''', (branch_code,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": f"Branch {branch_code} not found in database"})
        
        _, branch_name, price_filename, promo_filename = row
        
        # Step 1: Download files
        downloaded_files = download_branch_files(branch_code, price_filename, promo_filename)
        
        if not downloaded_files:
            return jsonify({"error": "Failed to download any files"})
        
        results = {
            "branch_code": branch_code,
            "branch_name": branch_name,
            "products": [],
            "promotions": [],
            "files_processed": [],
            "debug_info": []
        }
        
        # Step 2 & 3: Decompress and parse PriceFull
        if 'price_file' in downloaded_files:
            xml_content = decompress_gz_file(downloaded_files['price_file'])
            if xml_content:
                products = parse_price_xml(xml_content)
                results['products'] = products
                results['files_processed'].append(price_filename)
        
        # Step 2 & 3: Decompress and parse PromoFull  
        if 'promo_file' in downloaded_files:
            xml_content = decompress_gz_file(downloaded_files['promo_file'])
            if xml_content:
                promotions = parse_promo_xml(xml_content)
                results['promotions'] = promotions
                results['files_processed'].append(promo_filename)
        
        # Step 4: INSERT INTO DATABASE with proper relationships
        database_results = {
            "products_inserted": 0,
            "promotions_inserted": 0,
            "promotion_items_inserted": 0
        }
        
        if results['products'] or results['promotions']:
            print(f"💾 Step 4: Inserting data into database for Branch {branch_code}")
            
            # Insert products with clear chain/branch relationship
            if results['products']:
                try:
                    # Convert field names to match database method expectations
                    db_products = []
                    for product in results['products']:
                        db_product = {
                            'ItemCode': product['item_code'],
                            'ItemNm': product['item_name'], 
                            'ManufacturerName': product['manufacturer_name'],
                            'ManufacturerItemDescription': product['manufacturer_item_description'],
                            'ItemPrice': product['item_price'],
                            'UnitOfMeasurePrice': product['unit_of_measure_price'] or product['item_price'],
                            'UnitQty': product['unit_qty'] or 'יחידה',
                            'Quantity': product['quantity'] or '1',
                            'UnitOfMeasure': product['unit_of_measure'] or 'יחידה',
                            'bIsWeighted': product['is_weighted'] or '0',
                            'QtyInPackage': product['qty_in_package'] or '1',
                            'AllowDiscount': product['allow_discount'] or '1',
                            'ItemStatus': product['item_status'] or '1',
                            'ManufactureCountry': 'IL',
                            'PriceUpdateDate': product['price_update_date']
                        }
                        db_products.append(db_product)
                    
                    # Call with correct parameters: chain_code, branch_code, products_data
                    db.insert_products('CHAIN_001', branch_code, db_products)
                    database_results["products_inserted"] = len(db_products)
                    print(f"✅ Inserted {len(db_products)} products for Branch {branch_code} → CHAIN_001 (KingStore)")
                    
                    # ========================================
                    # POPULATE HIERARCHICAL DATABASE
                    # ========================================
                    try:
                        # Ensure KingStore exists in hierarchical DB
                        hierarchical_db.add_food_chain(
                            'CHAIN_001', 
                            'אלמשהדאוי קינג סטור בע"מ',
                            'https://kingstore.binaprojects.com/Main.aspx'
                        )
                        
                        # Get branch name from database
                        import sqlite3
                        conn = sqlite3.connect(db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT branch_name FROM branches WHERE branch_code = ?', (branch_code,))
                        branch_result = cursor.fetchone()
                        branch_name = branch_result[0] if branch_result else f'Branch {branch_code}'
                        conn.close()
                        
                        # Ensure branch exists in hierarchical DB
                        hierarchical_db.add_branch_to_chain(
                            'CHAIN_001', branch_code, branch_name,
                            price_filename, promo_filename
                        )
                        
                        # Convert products for hierarchical DB
                        hierarchical_products = []
                        for product in results['products']:
                            hierarchical_product = {
                                'item_code': product['item_code'],
                                'item_name': product['item_name'],
                                'manufacturer_name': product['manufacturer_name'],
                                'item_price': product['item_price'],
                                'unit_of_measure': product['unit_of_measure'],
                                'quantity': product['quantity'],
                                'price_update_date': product['price_update_date']
                            }
                            hierarchical_products.append(hierarchical_product)
                        
                        # Insert products into hierarchical structure
                        hierarchical_count = hierarchical_db.insert_branch_products(
                            'CHAIN_001', branch_code, hierarchical_products
                        )
                        
                        print(f"🏗️ Hierarchical DB: {hierarchical_count} products inserted into branch table")
                        
                        # ========================================
                        # INSERT PROMOTIONS INTO HIERARCHICAL DB
                        # ========================================
                        if results['promotions']:
                            try:
                                # Convert promotions for hierarchical DB
                                hierarchical_promotions = []
                                for promotion in results['promotions']:
                                    hierarchical_promotion = {
                                        'promotion_id': promotion['promotion_id'],
                                        'promotion_description': promotion['promotion_description'],
                                        'promotion_update_date': promotion['promotion_update_date'],
                                        'promotion_start_date': promotion['promotion_start_date'],
                                        'promotion_start_hour': promotion['promotion_start_hour'],
                                        'promotion_end_date': promotion['promotion_end_date'],
                                        'promotion_end_hour': promotion['promotion_end_hour'],
                                        'discounted_price': promotion['discounted_price'],
                                        'discounted_price_per_unit': promotion['discounted_price_per_unit'],
                                        'discount_rate': promotion['discount_rate'],
                                        'min_quantity': promotion['min_quantity'],
                                        'max_quantity': promotion['max_quantity'],
                                        'min_purchase_amount': promotion['min_purchase_amount'],
                                        'allow_multiple_discounts': promotion['allow_multiple_discounts'],
                                        'reward_type': promotion['reward_type'],
                                        'discount_type': promotion['discount_type'],
                                        'remarks': promotion['remarks'],
                                        'items': promotion['items']
                                    }
                                    hierarchical_promotions.append(hierarchical_promotion)
                                
                                # Insert promotions into hierarchical structure
                                hierarchical_promo_count = hierarchical_db.insert_branch_promotions(
                                    'CHAIN_001', branch_code, hierarchical_promotions
                                )
                                
                                print(f"🏗️ Hierarchical DB: {hierarchical_promo_count} promotions inserted into branch table")
                                
                            except Exception as hier_promo_error:
                                print(f"⚠️ Hierarchical DB promotion insertion failed: {str(hier_promo_error)}")
                        
                    except Exception as hier_error:
                        print(f"⚠️ Hierarchical DB insertion failed: {str(hier_error)}")
                    
                except Exception as e:
                    print(f"❌ Error inserting products: {str(e)}")
            
            # Insert promotions with clear chain/branch relationship  
            if results['promotions']:
                try:
                    # Convert field names to match database method expectations
                    db_promotions = []
                    for promotion in results['promotions']:
                        # Fix promotion items field names
                        fixed_items = []
                        for item in promotion.get('items', []):
                            fixed_item = {
                                'ItemCode': item.get('item_code', ''),
                                'IsGiftItem': item.get('is_gift_item', '0'),
                                'ItemType': item.get('item_type', '1')
                            }
                            fixed_items.append(fixed_item)
                        
                        # Helper function to ensure valid numeric values
                        def safe_num(val, default='0', as_int=False):
                            if not val or not val.strip():
                                return default
                            try:
                                if as_int:
                                    # Convert to float first, then to int to handle '1.1' -> 1
                                    return str(int(float(val.strip())))
                                else:
                                    return val.strip()
                            except (ValueError, TypeError):
                                return default
                        
                        db_promo = {
                            'PromotionId': promotion['promotion_id'] or '0',
                            'PromotionDescription': promotion['promotion_description'] or 'No description',
                            'PromotionStartDate': promotion['promotion_start_date'] or '2025-01-01',
                            'PromotionStartHour': '00:00:00',  # Default hour
                            'PromotionEndDate': promotion['promotion_end_date'] or '2025-12-31',
                            'PromotionEndHour': '23:59:00',    # Default hour
                            'RewardType': safe_num(promotion['reward_type'], '1', as_int=True),
                            'DiscountType': '1',  # Default discount type
                            'DiscountRate': safe_num(promotion['discount_rate'], '0.00'),
                            'DiscountedPrice': safe_num(promotion['discounted_price'], '0.00'),
                            'DiscountedPricePerMida': safe_num(promotion['discounted_price'], '0.00'),
                            'MinQty': safe_num(promotion['min_qty'], '1', as_int=True),
                            'MaxQty': safe_num(promotion['max_qty'], '0', as_int=True),
                            'MinPurchaseAmnt': '0.00',  # Default minimum purchase
                            'PromotionUpdateDate': promotion['promotion_update_date'] or '2025-01-01 00:00:00',
                            'PromotionItems': fixed_items  # Fixed promotion items with correct field names
                        }
                        db_promotions.append(db_promo)
                    
                    # DEBUG: Add info to response
                    results['debug_info'].append(f"About to insert {len(db_promotions)} promotions")
                    for i, p in enumerate(db_promotions[:1]):  # Show first one
                        results['debug_info'].append(f"Promotion {i+1}: {p['PromotionId']} - {p['PromotionDescription']}")
                        results['debug_info'].append(f"Items: {len(p.get('PromotionItems', []))}")
                    
                    # Call with correct parameters: chain_code, branch_code, promotions_data
                    try:
                        db.insert_promotions('CHAIN_001', branch_code, db_promotions)
                        database_results["promotions_inserted"] = len(db_promotions)
                        # Count total promotion items
                        total_items = sum(len(promo.get('PromotionItems', [])) for promo in db_promotions)
                        database_results["promotion_items_inserted"] = total_items
                        
                        results['debug_info'].append(f"SUCCESS: Inserted {len(db_promotions)} promotions")
                        results['debug_info'].append(f"SUCCESS: Inserted {total_items} promotion items")
                    except Exception as insert_error:
                        results['debug_info'].append(f"ERROR: Promotion insertion failed: {str(insert_error)}")
                        database_results["promotions_inserted"] = 0
                        database_results["promotion_items_inserted"] = 0
                    
                except Exception as e:
                    print(f"❌ Error inserting promotions: {str(e)}")
        
        results['database_insertion'] = database_results
        
        print(f"🎉 COMPLETE: Branch {branch_code} pipeline finished!")
        print(f"   📦 Products parsed: {len(results['products'])}")
        print(f"   🎯 Promotions parsed: {len(results['promotions'])}")
        print(f"   💾 Products in DB: {database_results['products_inserted']}")
        print(f"   💾 Promotions in DB: {database_results['promotions_inserted']}")
        
        return jsonify({
            "success": True,
            "message": f"Successfully processed and stored branch {branch_code}",
            "data": results
        })
        
    except Exception as e:
        log_message(f"❌ Error processing branch {branch_code}: {str(e)}")
        return jsonify({"error": f"Failed to process branch {branch_code}: {str(e)}"})

if __name__ == '__main__':
    log_message("🚀 Starting Flask server...")
    
    # Create data directory
    ensure_data_directory()
    
    # Check if database already has data
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM branches')
        branch_count = cursor.fetchone()[0]
        conn.close()
        
        if branch_count > 0:
            log_message(f"✅ Database already contains {branch_count} branches - skipping discovery")
        else:
            log_message("🔍 Database empty - running discovery...")
            discover_and_store_food_chain_data()
    except:
        log_message("🔍 Database not found - running discovery...")
        discover_and_store_food_chain_data()
    
    log_message("🌐 Server will be available at: http://localhost:5000")
    log_message("📋 Available endpoints:")
    log_message("   - GET /food-chains (all food chains)")
    log_message("   - GET /get-branches (from database)")
    log_message("   - GET /status (database status)")
    log_message("   - GET /process-branch/<code> (download, decompress, parse branch data)")
    log_message("🔄 Ready to serve food chain information from database!")
    
    app.run(host='0.0.0.0', port=5000, debug=False) 