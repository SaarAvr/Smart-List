from flask import Flask, jsonify, render_template_string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import sqlite3
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import requests
from database import FoodChainDatabase

app = Flask(__name__)

# Global database instance
db = FoodChainDatabase()

def log_message(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def ensure_data_directory():
    """Ensure the data directory exists"""
    os.makedirs("data", exist_ok=True)

def create_driver():
    """Create and configure Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Set download directory
    download_dir = "/Users/saar/repos/CursorProjects/smart_shared_list/branchesFiles"
    os.makedirs(download_dir, exist_ok=True)
    
    # Force download directory with command line arguments
    chrome_options.add_argument(f"--download-directory={download_dir}")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    return webdriver.Chrome(options=chrome_options)

@app.route('/')
def home():
    """Home page with links to all endpoints"""
    return jsonify({
        "message": "Food Chain Data Server",
        "endpoints": {
            "database_status": "/status",
            "phase1": "/phase1 - Discover food chains",
            "phase2": "/phase2 - Discover branches for KingStore",
            "phase3": "/phase3 - Download and process files",
            "update_file_names": "/update-file-names - Update file names for all branches",
            "update": "/update - Complete database update (file names + download + process + cleanup)",
            "food_chains": "/food-chains",
            "branches": "/branches/<chain_code>",
            "viewer": "/viewer"
        }
    })

@app.route('/status')
def status():
    """Get database status"""
    status_info = db.get_database_status()
    return jsonify(status_info)

@app.route('/phase1')
def phase1():
    """Phase 1: Discover all food chains from root URL"""
    try:
        log_message("🚀 Starting Phase 1: Food Chain Discovery...")
        
        # Check if database exists, create if not
        if not db.database_exists():
            log_message("📊 Creating new database...")
            db.initialize_database()
        
        # Create driver and navigate to the correct government page
        driver = create_driver()
        driver.get("https://www.gov.il/he/pages/cpfta_prices_regulations")
        
        # Wait for table to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
        )
        
        # Find all table rows containing food chain data
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        if not rows:
            log_message("❌ ERROR: No chain rows found")
            driver.quit()
            return jsonify({
                "status": "error",
                "error": "No food chain rows found on government website"
            })
        
        log_message(f"✅ Found {len(rows)} food chain rows on government site")
        
        discovered_chains = []
        
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
                    
                    # Basic validation - check link text and ensure we have name and URL
                    if "לצפי" not in link_text:
                        log_message(f"⏭️  Skipping row {i+1}: Link text doesn't contain 'לצפי' (got: '{link_text}')")
                        continue
                    
                    # Sequential chain code for all discovered chains
                    chain_code = f"CHAIN_{len(discovered_chains)+1:03d}"
                    
                    if chain_name and chain_url:
                        db.add_food_chain(chain_code, chain_name, chain_url)
                        discovered_chains.append({
                            "code": chain_code,
                            "name": chain_name,
                            "url": chain_url
                        })
                        log_message(f"   ✅ Discovered: {chain_name} ({chain_code})")
                        
            except Exception as e:
                log_message(f"⚠️  Warning: Could not extract chain {i+1}: {str(e)}")
                continue
        
        if not discovered_chains:
            log_message("⚠️ No food chains found on the government website")
        
        driver.quit()
        
        log_message(f"✅ Phase 1 Complete: Discovered {len(discovered_chains)} food chains")
        
        return jsonify({
            "status": "success",
            "phase": 1,
            "food_chains_discovered": len(discovered_chains),
            "food_chains": discovered_chains
        })
        
    except Exception as e:
        log_message(f"❌ Phase 1 failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/phase2')
def phase2():
    """Phase 2: Discover branches for KingStore (first food chain)"""
    try:
        log_message("🚀 Starting Phase 2: Branch Discovery for KingStore...")
        
        # Get KingStore from database
        food_chains = db.get_all_food_chains()
        if not food_chains:
            return jsonify({
                "status": "error",
                "error": "No food chains found. Run Phase 1 first."
            })
        
        # Focus on first food chain (KingStore)
        chain_code, chain_name, chain_url = food_chains[0]
        log_message(f"📊 Processing: {chain_name} ({chain_code})")
        log_message(f"🔗 Chain URL: {chain_url}")
        
        # Create branches table for this chain
        db.create_branches_table(chain_code)
        
        # Create driver and navigate to food chain URL
        driver = create_driver()
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
        discovered_branches = []
        branch_dict = {}
        
        for option in options_list:
            code = option.get_attribute("value").strip()
            name = option.text.strip()
            if code and name and code != "0":
                # Remove the code prefix from the name (e.g., "1 אום אלפחם" -> "אום אלפחם")
                clean_name = name.split(' ', 1)[1] if ' ' in name else name
                branch_dict[code] = clean_name
                
                # Add to database
                db.add_branch(chain_code, code, clean_name)
                discovered_branches.append({
                    "code": code,
                    "name": clean_name
                })
                log_message(f"   ✅ Discovered branch: {clean_name} (Code: {code})")
        
        driver.quit()
        
        if not discovered_branches:
            log_message("⚠️ No branches found on the food chain website")
        else:
            log_message(f"🎉 SUCCESS: Found {len(discovered_branches)} branches from {chain_name}!")
        
        log_message(f"✅ Phase 2 Complete: Discovered {len(discovered_branches)} branches for {chain_name}")
        
        return jsonify({
            "status": "success",
            "phase": 2,
            "chain_processed": chain_name,
            "branches_discovered": len(discovered_branches),
            "branches": discovered_branches
        })
        
    except Exception as e:
        log_message(f"❌ Phase 2 failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/phase3')
def phase3():
    """Phase 3: Download and process files for all branches"""
    try:
        log_message("🚀 Starting Phase 3: File Download and Processing...")
        
        # Get all food chains from database
        food_chains = db.get_all_food_chains()
        if not food_chains:
            return jsonify({
                "status": "error",
                "error": "No food chains found. Run Phase 1 first."
            })
        
        total_processed = 0
        chain_results = []
        
        # For now, focus on first food chain (KingStore)
        chain_code, chain_name, chain_url = food_chains[0]
        log_message(f"📊 Processing chain: {chain_name} ({chain_code})")
        
        # Get all branches for this chain
        try:
            branches = db.get_branches(chain_code)
            if not branches:
                return jsonify({
                    "status": "error",
                    "error": f"No branches found for {chain_name}. Run Phase 2 first."
                })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": f"No branch table exists for {chain_name}. Run Phase 2 first."
            })
        
        log_message(f"🏪 Found {len(branches)} branches for {chain_name}")
        
        branch_results = []

        # Prepare a single driver and index the chain table once
        driver = create_driver()
        driver.get(chain_url)
        WebDriverWait(driver, 30).until(
            lambda d: any(len(row.find_elements(By.TAG_NAME, "td")) > 0 
                          for row in d.find_elements(By.CSS_SELECTOR, "table#myTable tr"))
        )

        rows = driver.find_elements(By.CSS_SELECTOR, "table#myTable tr")
        log_message(f"📄 Indexed {len(rows)} rows from chain table")

        # Get file names from database (no need to scan entire table)
        log_message("📋 Getting file names from database...")

        # Helper to wait for a file to appear (check both directories)
        def wait_for_file(path, timeout_seconds=90):
            start = time.time()
            system_downloads = os.path.expanduser("~/Downloads")
            filename = os.path.basename(path)
            system_path = os.path.join(system_downloads, filename)
            
            while time.time() - start < timeout_seconds:
                # Check our target directory first
                if os.path.exists(path):
                    return True
                # Check system Downloads directory
                if os.path.exists(system_path):
                    log_message(f"   📁 Found file in system Downloads, moving to {path}")
                    try:
                        import shutil
                        shutil.move(system_path, path)
                        return True
                    except Exception as e:
                        log_message(f"   ❌ Error moving file: {e}")
                        return False
                time.sleep(1)
            return False

        # Ensure download dir
        download_dir = os.path.abspath("branchesFiles")
        os.makedirs(download_dir, exist_ok=True)

        for branch_code, branch_name, price_file_name, promo_file_name in branches:
            try:
                log_message(f"📦 Processing branch {branch_code}: {branch_name}")

                # Skip if no file names available
                if not price_file_name and not promo_file_name:
                    log_message(f"   ⚠️ No file names available for branch {branch_code}, skipping...")
                    continue

                # Create tables for this branch
                db.create_products_table(chain_code, branch_code)
                db.create_promotions_table(chain_code, branch_code)
                
                # Clear existing data to avoid constraint conflicts
                log_message(f"   🧹 Clearing existing data for branch {branch_code}")
                db.clear_branch_data(chain_code, branch_code)
                
                branch_processed = 0

                # Download and process PriceFull file (strict)
                actual_price_file = None
                if price_file_name and "PriceFull" in price_file_name:
                    log_message(f"   🔍 Looking for price file: {price_file_name}")
                    expected_path = os.path.join(download_dir, price_file_name)
                    
                    # Find the row containing this file and extract the button
                    file_found = False
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 6:
                            continue
                        row_file_name = cells[0].text.strip()
                        if row_file_name == price_file_name:
                            log_message(f"   ✅ Found file in table: {price_file_name}")
                            # Extract download button from this row
                            download_buttons = cells[5].find_elements(By.TAG_NAME, "button")
                            if download_buttons:
                                btn = download_buttons[0]
                                log_message(f"   🖱️ Clicking download for {price_file_name}")
                                driver.execute_script("arguments[0].click();", btn)
                                if wait_for_file(expected_path):
                                    log_message(f"   📄 Processing price file: {expected_path}")
                                    products_processed = process_price_file(chain_code, branch_code, expected_path)
                                    branch_processed += products_processed
                                    actual_price_file = price_file_name
                                    log_message(f"   ✅ Processed {products_processed} products from price file")
                                    file_found = True
                                    break
                                else:
                                    log_message(f"   ❌ Timed out waiting for price file: {expected_path}")
                            else:
                                log_message(f"   ❌ No download button found for {price_file_name}")
                            break
                    
                    if not file_found:
                        log_message(f"   ❌ Could not find file in table: {price_file_name}")

                # Download and process PromoFull file (strict)
                actual_promo_file = None
                if promo_file_name and "PromoFull" in promo_file_name:
                    log_message(f"   🔍 Looking for promo file: {promo_file_name}")
                    expected_path = os.path.join(download_dir, promo_file_name)
                    
                    # Find the row containing this file and extract the button
                    file_found = False
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 6:
                            continue
                        row_file_name = cells[0].text.strip()
                        if row_file_name == promo_file_name:
                            log_message(f"   ✅ Found file in table: {promo_file_name}")
                            # Extract download button from this row
                            download_buttons = cells[5].find_elements(By.TAG_NAME, "button")
                            if download_buttons:
                                btn = download_buttons[0]
                                log_message(f"   🖱️ Clicking download for {promo_file_name}")
                                driver.execute_script("arguments[0].click();", btn)
                                if wait_for_file(expected_path):
                                    log_message(f"   📄 Processing promo file: {expected_path}")
                                    promotions_processed = process_promo_file(chain_code, branch_code, expected_path)
                                    branch_processed += promotions_processed
                                    actual_promo_file = promo_file_name
                                    log_message(f"   ✅ Processed {promotions_processed} promotions from promo file")
                                    file_found = True
                                    break
                                else:
                                    log_message(f"   ❌ Timed out waiting for promo file: {expected_path}")
                            else:
                                log_message(f"   ❌ No download button found for {promo_file_name}")
                            break
                    
                    if not file_found:
                        log_message(f"   ❌ Could not find file in table: {promo_file_name}")

                # Update database with actual processed file names (Option A)
                if actual_price_file or actual_promo_file:
                    try:
                        conn = sqlite3.connect(db.db_path)
                        cur = conn.cursor()
                        branches_table = f"branches_{chain_code}"
                        
                        if actual_price_file:
                            cur.execute(f"UPDATE {branches_table} SET price_file_name = ? WHERE branch_code = ?", 
                                      (actual_price_file, branch_code))
                            log_message(f"   📝 Updated price file name in database: {actual_price_file}")
                        
                        if actual_promo_file:
                            cur.execute(f"UPDATE {branches_table} SET promo_file_name = ? WHERE branch_code = ?", 
                                      (actual_promo_file, branch_code))
                            log_message(f"   📝 Updated promo file name in database: {actual_promo_file}")
                        
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        log_message(f"   ⚠️ Error updating file names in database: {str(e)}")

                # Clean up downloaded files after successful processing
                files_to_cleanup = []
                if actual_price_file:
                    files_to_cleanup.append(os.path.join(download_dir, actual_price_file))
                if actual_promo_file:
                    files_to_cleanup.append(os.path.join(download_dir, actual_promo_file))
                
                for file_path in files_to_cleanup:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            log_message(f"   🗑️ Cleaned up file: {os.path.basename(file_path)}")
                    except Exception as e:
                        log_message(f"   ⚠️ Error cleaning up file {file_path}: {str(e)}")

                total_processed += branch_processed
                branch_results.append({
                    "branch_code": branch_code,
                    "branch_name": branch_name,
                    "files_processed": branch_processed,
                    "price_file": actual_price_file or price_file_name,
                    "promo_file": actual_promo_file or promo_file_name
                })

                log_message(f"   ✅ Completed branch {branch_code}: {branch_processed} items processed")

            except Exception as e:
                log_message(f"   ❌ Error processing branch {branch_code}: {str(e)}")
                branch_results.append({
                    "branch_code": branch_code,
                    "branch_name": branch_name,
                    "error": str(e)
                })

        # Close the single driver
        try:
            driver.quit()
        except Exception:
            pass
        
        chain_results.append({
            "chain_name": chain_name,
            "chain_code": chain_code,
            "branches_processed": len(branch_results),
            "total_items_processed": total_processed,
            "branch_results": branch_results
        })
        
        log_message(f"🎉 Phase 3 Complete: Processed {total_processed} items across {len(branch_results)} branches")
        
        return jsonify({
            "status": "success",
            "phase": 3,
            "total_items_processed": total_processed,
            "chains_processed": len(chain_results),
            "chain_results": chain_results
        })
        
    except Exception as e:
        log_message(f"❌ Phase 3 failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

def download_branch_files(branch_code, price_filename, promo_filename):
    """Download actual files from food chain website"""
    log_message(f"📥 Downloading files for branch {branch_code}")
    
    downloaded_files = {}
    driver = None
    
    try:
        # Get chain URL from database
        food_chains = db.get_all_food_chains()
        if not food_chains:
            return None
        
        chain_code, chain_name, chain_url = food_chains[0]  # KingStore
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Set download directory
        download_dir = "/Users/saar/repos/CursorProjects/smart_shared_list/branchesFiles"
        os.makedirs(download_dir, exist_ok=True)
        
        # Force download directory with command line arguments
        chrome_options.add_argument(f"--download-directory={download_dir}")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,
            "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
        
        log_message(f"🌐 Navigating to {chain_name} page...")
        driver.get(chain_url)
        
        # Wait for the page to load and find the file table
        WebDriverWait(driver, 30).until(
            lambda d: any(len(row.find_elements(By.TAG_NAME, "td")) > 0 
                         for row in d.find_elements(By.CSS_SELECTOR, "table#myTable tr"))
        )
        
        # Find all table rows
        rows = driver.find_elements(By.CSS_SELECTOR, "table#myTable tr")
        files_downloaded = 0
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                continue
                
            file_name = cells[0].text.strip()
            row_branch_code = cells[1].text.strip()
            
            # Check if this row matches our target branch and file patterns
            branch_matches = row_branch_code.startswith(branch_code + ' ') or row_branch_code == branch_code
            
            # Check for file pattern matches - STRICT PriceFull/PromoFull only
            is_price_file = ('PriceFull' in file_name and branch_code in file_name and file_name == price_filename)
            is_promo_file = ('PromoFull' in file_name and branch_code in file_name and file_name == promo_filename)
            
            if branch_matches and (is_price_file or is_promo_file):
                log_message(f"📥 Found target file: {file_name}")
                
                # Look for download button in the last cell
                download_buttons = cells[5].find_elements(By.TAG_NAME, "button")
                for button in download_buttons:
                    log_message(f"🖱️ Clicking download button for {file_name}")
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(3)  # Wait for download to start
                    files_downloaded += 1
                    
                    # Store the actual downloaded file name and path
                    if is_price_file:
                        downloaded_files['price_file'] = os.path.join(download_dir, file_name)
                        downloaded_files['price_filename'] = file_name
                    elif is_promo_file:
                        downloaded_files['promo_file'] = os.path.join(download_dir, file_name)
                        downloaded_files['promo_filename'] = file_name
                    break
        
        driver.quit()
        
        if files_downloaded > 0:
            log_message(f"✅ Successfully initiated {files_downloaded} file downloads")
            time.sleep(5)  # Wait for files to finish downloading
        else:
            log_message("❌ No matching files found for download")
            
        return downloaded_files
        
    except Exception as e:
        log_message(f"❌ Error downloading files: {str(e)}")
        if driver:
            driver.quit()
        return None

def decompress_gz_file(filepath):
    """Read XML file (handles .gz, .zip, and regular .xml files)"""
    log_message(f"📦 Reading file: {filepath}")
    
    try:
        # Check file signature to determine actual format
        with open(filepath, 'rb') as f:
            signature = f.read(2)
        
        if signature == b'PK':
            # ZIP file
            log_message("🗜️ Detected ZIP file, extracting...")
            import zipfile
            with zipfile.ZipFile(filepath, 'r') as zip_file:
                xml_files = [name for name in zip_file.namelist() if name.endswith('.xml')]
                if xml_files:
                    with zip_file.open(xml_files[0]) as xml_file:
                        xml_content = xml_file.read().decode('utf-8')
                else:
                    raise Exception("No XML file found in ZIP archive")
                    
        elif signature == b'\x1f\x8b':
            # Gzip file
            log_message("🗜️ Detected gzip file, decompressing...")
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                xml_content = f.read()
        else:
            # Regular XML file
            log_message("📄 Regular XML file, reading directly...")
            with open(filepath, 'r', encoding='utf-8') as f:
                xml_content = f.read()
                
        log_message(f"✅ File read successfully, XML size: {len(xml_content)} characters")
        return xml_content
    except Exception as e:
        log_message(f"❌ Error reading {filepath}: {str(e)}")
        return None

def process_price_file(chain_code, branch_code, file_path):
    """Process PriceFull XML file and store products in database"""
    try:
        xml_content = decompress_gz_file(file_path)
        if not xml_content:
            return 0
        
        # Parse XML and extract products
        root = ET.fromstring(xml_content)
        products_processed = 0
        
        # Find all item elements (adjust XPath based on actual XML structure)
        for item in root.findall('.//Item'):
            try:
                product_data = {
                    'item_code': item.find('ItemCode').text if item.find('ItemCode') is not None else '',
                    # Some datasets use <ItemNm> instead of <ItemName>
                    'item_name': (
                        item.find('ItemName').text if item.find('ItemName') is not None and item.find('ItemName').text is not None
                        else (item.find('ItemNm').text if item.find('ItemNm') is not None else '')
                    ),
                    'manufacturer_name': item.find('ManufacturerName').text if item.find('ManufacturerName') is not None else '',
                    'item_price': item.find('ItemPrice').text if item.find('ItemPrice') is not None else '',
                    # Some datasets use <UnitQty> in addition or instead
                    'unit_of_measure': (
                        item.find('UnitOfMeasure').text if item.find('UnitOfMeasure') is not None and item.find('UnitOfMeasure').text is not None
                        else (item.find('UnitQty').text if item.find('UnitQty') is not None else '')
                    ),
                    'quantity': item.find('Quantity').text if item.find('Quantity') is not None else '',
                    'price_update_date': item.find('PriceUpdateDate').text if item.find('PriceUpdateDate') is not None else ''
                }
                
                db.add_product(chain_code, branch_code, product_data)
                products_processed += 1
                
            except Exception as e:
                log_message(f"   ⚠️ Error processing product: {str(e)}")
                continue
        
        log_message(f"   📊 Processed {products_processed} products from price file")
        return products_processed
        
    except Exception as e:
        log_message(f"❌ Error processing price file: {str(e)}")
        return 0

def process_promo_file(chain_code, branch_code, file_path):
    """Process PromoFull XML file and store promotions in database"""
    try:
        xml_content = decompress_gz_file(file_path)
        if not xml_content:
            return 0
        
        # Parse XML and extract promotions
        root = ET.fromstring(xml_content)
        promotions_processed = 0
        
        # Find all promotion elements (adjust XPath based on actual XML structure)
        for promo in root.findall('.//Promotion'):
            try:
                # Extract promotion data
                # Handle alternate field names and join date+hour where available
                def text_or(elem_name: str) -> str:
                    elem = promo.find(elem_name)
                    return elem.text if elem is not None and elem.text is not None else ''

                start_date = text_or('PromotionStartDate')
                start_hour = text_or('PromotionStartHour')
                end_date = text_or('PromotionEndDate')
                end_hour = text_or('PromotionEndHour')
                start_dt = f"{start_date} {start_hour}".strip() if start_date or start_hour else ''
                end_dt = f"{end_date} {end_hour}".strip() if end_date or end_hour else ''

                # Min/Max quantities with proper tag names
                min_qty = text_or('MinQty') or text_or('MinQuantity')
                max_qty = text_or('MaxQty') or text_or('MaxQuantity')

                # Discounted price per unit/Mida
                per_unit = text_or('DiscountedPricePerMida') or text_or('DiscountedPricePerUnit')

                promotion_data = {
                    'promotion_id': text_or('PromotionId'),
                    'promotion_description': text_or('PromotionDescription'),
                    'discounted_price': text_or('DiscountedPrice'),
                    'min_quantity': min_qty,
                    'promotion_end_date': end_dt or end_date,
                    'promotion_start_date': start_dt or start_date,
                    'max_quantity': max_qty,
                    'discounted_price_per_unit': per_unit,
                    'item_codes': [],
                    'items_count': 0,
                    'related_item_codes': ''
                }
                
                # Extract item codes under PromotionItems; fallback to any ItemCode
                item_codes_set = set()
                for it in promo.findall('.//PromotionItems//Item'):
                    code_el = it.find('ItemCode')
                    if code_el is not None and code_el.text:
                        item_codes_set.add(code_el.text)
                if not item_codes_set:
                    for code in promo.findall('.//ItemCode'):
                        if code.text:
                            item_codes_set.add(code.text)
                item_codes = sorted(item_codes_set)
                promotion_data['item_codes'] = item_codes
                # Promotion parsed successfully
                # Prefer the declared count attribute if present and numeric
                items_count_attr = 0
                pi_node = promo.find('PromotionItems')
                if pi_node is not None:
                    try:
                        items_count_attr = int(pi_node.get('count') or 0)
                    except Exception:
                        items_count_attr = 0
                promotion_data['items_count'] = items_count_attr or len(item_codes)
                # We no longer store a redundant related list string in DB usage
                promotion_data['related_item_codes'] = ''
                
                db.add_promotion(chain_code, branch_code, promotion_data)
                promotions_processed += 1
                
            except Exception as e:
                log_message(f"   ⚠️ Error processing promotion: {str(e)}")
                continue
        
        log_message(f"   📊 Processed {promotions_processed} promotions from promo file")
        return promotions_processed
        
    except Exception as e:
        log_message(f"❌ Error processing promo file: {str(e)}")
        return 0

@app.route('/update-file-names')
def update_file_names():
    """Update file names for all branches of all food chains"""
    try:
        log_message("🚀 Starting File Name Update for All Food Chains...")
        
        # Get all food chains from database
        food_chains = db.get_all_food_chains()
        if not food_chains:
            return jsonify({
                "status": "error",
                "error": "No food chains found. Run Phase 1 first."
            })
        
        total_updates = 0
        chain_results = []
        
        for chain_code, chain_name, chain_url in food_chains:
            try:
                log_message(f"📊 Processing chain: {chain_name} ({chain_code})")
                
                # Get all branches for this chain
                try:
                    branches = db.get_branches(chain_code)
                    if not branches:
                        log_message(f"⚠️ No branches found for {chain_name}, skipping...")
                        continue
                except Exception as e:
                    log_message(f"⚠️ No branch table exists for {chain_name}, skipping...")
                    continue
                
                log_message(f"🏪 Found {len(branches)} branches for {chain_name}")
                
                # Create driver and navigate to chain URL
                driver = create_driver()
                driver.get(chain_url)
                
                # Wait for the file table to be populated
                WebDriverWait(driver, 30).until(
                    lambda d: any(len(row.find_elements(By.TAG_NAME, "td")) > 0 for row in d.find_elements(By.CSS_SELECTOR, "table#myTable tr"))
                )
                
                chain_rows = driver.find_elements(By.CSS_SELECTOR, "table#myTable tr")
                log_message(f"📁 Found {len(chain_rows)} file entries for {chain_name}")
                
                # Parse file table to find latest files for each branch
                branch_files = {}
                
                for row in chain_rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:
                        continue
                    
                    file_name = cells[0].text.strip()
                    branch_code_full = cells[1].text.strip()
                    
                    # Skip empty or invalid entries
                    if not file_name or not branch_code_full:
                        continue
                    
                    # Extract just the numeric code from "339 יפו תלאביב מכללה" -> "339"
                    branch_code = branch_code_full.split(' ', 1)[0] if ' ' in branch_code_full else branch_code_full
                    
                    # Extract date from end of filename: PriceFull7290058108879-001-202507271024.gz -> 202507271024
                    import re
                    match = re.search(r'-(\d{12})\.gz$', file_name)
                    file_date = match.group(1) if match else ""
                    
                    # Determine file type - we need PriceFull and PromoFull files
                    if "PriceFull" in file_name:
                        file_type = "PriceFull"
                    elif "PromoFull" in file_name:
                        file_type = "PromoFull"
                    else:
                        continue
                    
                    # Track latest file for each branch
                    if branch_code not in branch_files:
                        branch_files[branch_code] = {"PriceFull": ("", ""), "PromoFull": ("", "")}
                    
                    if file_type == "PriceFull" and file_date > branch_files[branch_code]["PriceFull"][1]:
                        branch_files[branch_code]["PriceFull"] = (file_name, file_date)
                    if file_type == "PromoFull" and file_date > branch_files[branch_code]["PromoFull"][1]:
                        branch_files[branch_code]["PromoFull"] = (file_name, file_date)
                
                driver.quit()
                
                # Update database with file names for each branch
                chain_updates = 0
                for branch_code, branch_name, existing_price_file, existing_promo_file in branches:
                    if branch_code in branch_files:
                        price_file = branch_files[branch_code]["PriceFull"][0]
                        promo_file = branch_files[branch_code]["PromoFull"][0]
                        
                        # Update branch with file names
                        db.add_branch(chain_code, branch_code, branch_name, price_file, promo_file)
                        chain_updates += 1
                        log_message(f"   ✅ Updated branch {branch_code}: Price={price_file}, Promo={promo_file}")
                    else:
                        log_message(f"   ⚠️ No files found for branch {branch_code}")
                
                total_updates += chain_updates
                chain_results.append({
                    "chain_name": chain_name,
                    "chain_code": chain_code,
                    "branches_updated": chain_updates,
                    "total_branches": len(branches)
                })
                
                log_message(f"✅ Completed {chain_name}: {chain_updates}/{len(branches)} branches updated")
                
            except Exception as e:
                log_message(f"❌ Error processing chain {chain_name}: {str(e)}")
                chain_results.append({
                    "chain_name": chain_name,
                    "chain_code": chain_code,
                    "error": str(e)
                })
        
        log_message(f"🎉 File name update complete! Total updates: {total_updates}")
        
        return jsonify({
            "status": "success",
            "total_updates": total_updates,
            "chains_processed": len(chain_results),
            "chain_results": chain_results
        })
        
    except Exception as e:
        log_message(f"❌ File name update failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/update')
def update():
    """Integrated update: Update file names + Download & Process + Cleanup"""
    try:
        log_message("🔄 Starting Integrated Update Process...")
        
        # Step 1: Update file names (using the proven update_file_names logic)
        log_message("📝 Step 1: Updating file names...")
        try:
            # Call the existing update_file_names endpoint internally
            from flask import Flask
            with app.test_client() as client:
                response = client.get('/update-file-names')
                update_result = response.get_json()
                
                if update_result.get('status') != 'success':
                    return jsonify({
                        "status": "error", 
                        "error": f"File name update failed: {update_result.get('error', 'Unknown error')}"
                    })
                
                total_updates = update_result.get('total_updates', 0)
                log_message(f"✅ Step 1 Complete: Updated {total_updates} branches")
            
        except Exception as e:
            return jsonify({
                "status": "error", 
                "error": f"Failed in Step 1 (update file names): {str(e)}"
            })
        
        # Step 2: Download and process files (simplified approach using existing Phase 3)
        log_message("📥 Step 2: Downloading and processing files...")
        try:
            # Just call the existing phase3 endpoint internally
            from flask import Flask
            with app.test_client() as client:
                response = client.get('/phase3')
                phase3_result = response.get_json()
                
                if phase3_result.get('status') != 'success':
                    return jsonify({
                        "status": "error", 
                        "error": f"Phase 3 failed: {phase3_result.get('error', 'Unknown error')}"
                    })
                
                total_processed = phase3_result.get('total_items_processed', 0)
                log_message(f"✅ Step 2 Complete: Processed {total_processed} items")
            
        except Exception as e:
            return jsonify({
                "status": "error", 
                "error": f"Failed in Step 2 (download & process): {str(e)}"
            })
        
        log_message("🎉 Integrated Update Complete!")
        
        return jsonify({
            "status": "success",
            "message": "Update completed successfully",
            "file_updates": total_updates,
            "items_processed": total_processed
        })
        
    except Exception as e:
        log_message(f"❌ Update failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/debug-files')
def debug_files():
    """Debug endpoint to check file table indexing"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        
        # Get first food chain
        food_chains = db.get_all_food_chains()
        if not food_chains:
            return jsonify({"error": "No food chains found"})
        
        chain_code, chain_name, chain_url = food_chains[0]
        
        # Get first few branches
        branches = db.get_branches(chain_code)[:3]  # Just first 3 for debugging
        
        # Create driver and navigate to chain URL
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument(f"--download-directory=/Users/saar/repos/CursorProjects/smart_shared_list/branchesFiles")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": "/Users/saar/repos/CursorProjects/smart_shared_list/branchesFiles",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        })
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(chain_url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            lambda d: any(len(row.find_elements(By.TAG_NAME, "td")) > 0 
                          for row in d.find_elements(By.CSS_SELECTOR, "table tr"))
        )
        
        # Try to search for PriceFull files like the user did in the screenshot
        try:
            search_box = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[placeholder*='search'], input[name*='search']")
            search_box.clear()
            search_box.send_keys("pricefull")
            search_box.submit()
            time.sleep(3)  # Wait for search results
            log_message("🔍 Searched for 'pricefull' files")
        except Exception as e:
            log_message(f"⚠️ Could not search: {e}")
            # Continue without search
        
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        
        # Build file index with debugging
        table_index = {}
        indexed_files = []
        
        for row in rows[:100]:  # Check first 100 rows for debugging
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                continue
            file_name = cells[0].text.strip()
            branch_code_full = cells[1].text.strip()
            short_code = branch_code_full.split(' ', 1)[0] if ' ' in branch_code_full else branch_code_full
            
            # Show ALL files for debugging, not just PriceFull/PromoFull
            buttons = cells[5].find_elements(By.TAG_NAME, "button")
            has_button = len(buttons) > 0
            
            indexed_files.append({
                "file_name": file_name,
                "branch_code": short_code,
                "branch_full": branch_code_full,
                "has_button": has_button,
                "is_target": "PriceFull" in file_name or "PromoFull" in file_name,
                "cell_count": len(cells)
            })
            
            # Only add to lookup table if it's a target file
            if "PriceFull" in file_name or "PromoFull" in file_name:
                table_index[(short_code, file_name)] = has_button
        
        driver.quit()
        
        # Check what we're looking for vs what we found
        lookups = []
        for branch_code, branch_name, price_file, promo_file in branches:
            price_key = (branch_code, price_file) if price_file else None
            promo_key = (branch_code, promo_file) if promo_file else None
            
            lookups.append({
                "branch_code": branch_code,
                "branch_name": branch_name,
                "price_file": price_file,
                "promo_file": promo_file,
                "price_found": table_index.get(price_key, False) if price_key else None,
                "promo_found": table_index.get(promo_key, False) if promo_key else None
            })
        
        return jsonify({
            "status": "success",
            "chain_url": chain_url,
            "total_rows": len(rows),
            "indexed_files": indexed_files,
            "branch_lookups": lookups
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/reprocess-local')
def reprocess_local():
    """Reprocess already-downloaded files from the branchesFiles directory to refresh DB (no downloads)."""
    try:
        food_chains = db.get_all_food_chains()
        if not food_chains:
            return jsonify({"status": "error", "error": "No food chains found"})
        chain_code, chain_name, chain_url = food_chains[0]

        try:
            branches = db.get_branches(chain_code)
        except Exception:
            return jsonify({"status": "error", "error": f"No branches table for {chain_code}"})

        download_dir = os.path.abspath("branchesFiles")
        total = 0
        branch_results = []

        for branch_code, branch_name, price_file_name, promo_file_name in branches:
            processed = 0
            # Ensure tables exist and clear previous rows to avoid stale values
            try:
                db.create_products_table(chain_code, branch_code)
                db.create_promotions_table(chain_code, branch_code)
                # Clear existing data before reprocessing
                db.clear_branch_data(chain_code, branch_code)
            except Exception:
                pass

            if price_file_name:
                price_path = os.path.join(download_dir, price_file_name)
                if os.path.exists(price_path):
                    processed += process_price_file(chain_code, branch_code, price_path)
            if promo_file_name:
                promo_path = os.path.join(download_dir, promo_file_name)
                if os.path.exists(promo_path):
                    processed += process_promo_file(chain_code, branch_code, promo_path)
            total += processed
            branch_results.append({
                "branch_code": branch_code,
                "branch_name": branch_name,
                "items_processed": processed
            })

        return jsonify({
            "status": "success",
            "chain_code": chain_code,
            "total_items_processed": total,
            "branches": branch_results
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/food-chains')
def get_food_chains():
    """Get all food chains from database"""
    try:
        food_chains = db.get_all_food_chains()
        return jsonify({
            "status": "success",
            "food_chains": [
                {
                    "code": code,
                    "name": name,
                    "url": url
                }
                for code, name, url in food_chains
            ]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/branches/<chain_code>')
def get_branches(chain_code):
    """Get branches for a specific food chain"""
    try:
        branches = db.get_branches(chain_code)
        return jsonify({
            "status": "success",
            "chain_code": chain_code,
            "branches": [
                {
                    "code": code,
                    "name": name,
                    "price_file": price_file,
                    "promo_file": promo_file
                }
                for code, name, price_file, promo_file in branches
            ]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/branch/<chain_code>/<branch_code>')
def get_branch_details(chain_code, branch_code):
    """Return branch metadata, products, and promotions for viewer"""
    try:
        # Metadata from branches table
        branches = db.get_branches(chain_code)
        branch_meta = None
        for code, name, price_file, promo_file in branches:
            if code == branch_code:
                branch_meta = {
                    "code": code,
                    "name": name,
                    "price_file": price_file,
                    "promo_file": promo_file,
                }
                break

        if branch_meta is None:
            return jsonify({"status": "error", "error": "Branch not found"}), 404

        # Fetch products
        products_table = f"products_{chain_code}_{branch_code}"
        products = []
        try:
            conn = sqlite3.connect(db.db_path)
            cur = conn.cursor()
            cur.execute(f"""
                SELECT item_code, item_name, manufacturer_name, item_price,
                       unit_of_measure, quantity, price_update_date
                FROM {products_table}
                ORDER BY CAST(item_price AS REAL) DESC
            """)
            for row in cur.fetchall():
                products.append({
                    "item_code": row[0],
                    "item_name": row[1],
                    "manufacturer_name": row[2],
                    "item_price": row[3],
                    "unit_of_measure": row[4],
                    "quantity": row[5],
                    "price_update_date": row[6],
                })
            conn.close()
        except Exception:
            products = []

        # Fetch promotions
        promotions_table = f"promotions_{chain_code}_{branch_code}"
        promotion_items_table = f"promotion_items_{chain_code}_{branch_code}"
        promotions = []
        try:
            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Join with distinct item counts to avoid relying on stored columns
            cur.execute(f"""
                SELECT p.promotion_id,
                       p.promotion_description,
                       p.discounted_price,
                       p.min_quantity,
                       p.promotion_end_date,
                       p.promotion_start_date,
                       p.max_quantity,
                       p.discounted_price_per_unit,
                       COALESCE(ic.cnt, 0) AS item_count
                FROM {promotions_table} p
                LEFT JOIN (
                    SELECT promotion_id, COUNT(DISTINCT item_code) AS cnt
                    FROM {promotion_items_table}
                    GROUP BY promotion_id
                ) ic ON ic.promotion_id = p.promotion_id
                ORDER BY CAST(p.discounted_price AS REAL) DESC
            """)
            rows = cur.fetchall()
            log_message(f"Promotions rows fetched: {len(rows)} from {promotions_table}")
            for prow in rows:
                promotion_id = prow["promotion_id"]
                # Fetch distinct item codes for this promotion
                cur.execute(f"SELECT DISTINCT item_code FROM {promotion_items_table} WHERE promotion_id = ?", (promotion_id,))
                item_codes = [r[0] for r in cur.fetchall()]
                # Promotion data retrieved
                promotions.append({
                    "promotion_id": promotion_id,
                    "promotion_description": prow["promotion_description"],
                    "discounted_price": prow["discounted_price"],
                    "min_quantity": prow["min_quantity"],
                    "promotion_end_date": prow["promotion_end_date"],
                    "promotion_start_date": prow["promotion_start_date"],
                    "max_quantity": prow["max_quantity"],
                    "discounted_price_per_unit": prow["discounted_price_per_unit"],
                    "item_codes": item_codes,
                    "item_count": len(item_codes),
                })
            conn.close()
        except Exception as e:
            log_message(f"Promotions query error: {str(e)}")
            return jsonify({"status": "error", "error": str(e)})

        return jsonify({
            "status": "success",
            "chain_code": chain_code,
            "branch": branch_meta,
            "products": products,
            "promotions": promotions,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/viewer')
def viewer():
    """Hierarchical web viewer for the database"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hierarchical Food Chain Database</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 0; 
                background-color: #f5f5f5; 
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 20px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            }
            .header h1 { 
                margin: 0; 
                font-size: 24px; 
                display: flex; 
                align-items: center; 
            }
            .header .icon { 
                font-size: 28px; 
                margin-right: 10px; 
            }
            .nav-path { 
                font-size: 14px; 
                opacity: 0.9; 
                margin-top: 5px; 
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px; 
            }
            .breadcrumbs { 
                background: white; 
                padding: 15px; 
                border-radius: 8px; 
                margin-bottom: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                display: flex; 
                align-items: center; 
                justify-content: space-between; 
            }
            .breadcrumb-path { 
                display: flex; 
                align-items: center; 
                font-size: 16px; 
            }
            .breadcrumb-item { 
                display: flex; 
                align-items: center; 
                margin-right: 10px; 
            }
            .breadcrumb-item .icon { 
                margin-right: 5px; 
                font-size: 18px; 
            }
            .back-btn { 
                background: #ff6b35; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer; 
                font-size: 14px; 
            }
            .back-btn:hover { 
                background: #e55a2b; 
            }
            .chain-header { 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            }
            .chain-title { 
                font-size: 24px; 
                margin: 0 0 10px 0; 
                display: flex; 
                align-items: center; 
            }
            .chain-title .icon { 
                margin-right: 10px; 
                font-size: 28px; 
            }
            .metadata-section { 
                background: #e8f5e8; 
                border: 1px solid #4caf50; 
                border-radius: 8px; 
                padding: 20px; 
                margin-bottom: 20px; 
            }
            .metadata-title { 
                font-size: 18px; 
                font-weight: bold; 
                margin-bottom: 15px; 
                display: flex; 
                align-items: center; 
            }
            .metadata-title .icon { 
                margin-right: 8px; 
            }
            .metadata-grid { 
                display: flex; 
                flex-direction: column; 
                gap: 10px; 
            }
            .metadata-item { 
                background: white; 
                padding: 12px 15px; 
                border-radius: 5px; 
                border-left: 4px solid #4caf50; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
            }
            .metadata-label { 
                font-weight: bold; 
                color: #666; 
                font-size: 14px; 
                text-transform: uppercase; 
                min-width: 120px; 
            }
            .metadata-value { 
                font-size: 14px; 
                color: #333; 
                text-align: right; 
                word-break: break-all; 
            }
            .branches-section { 
                background: white; 
                border-radius: 8px; 
                padding: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            }
            .branches-title { 
                font-size: 18px; 
                font-weight: bold; 
                margin-bottom: 15px; 
                display: flex; 
                align-items: center; 
            }
            .branches-title .icon { 
                margin-right: 8px; 
            }
            .branch-item { 
                background: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 5px; 
                padding: 15px; 
                margin-bottom: 10px; 
            }
            .branch-header { 
                font-weight: bold; 
                font-size: 16px; 
                margin-bottom: 8px; 
                color: #333; 
            }
            .branch-details { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 10px; 
                font-size: 14px; 
            }
            .branch-detail { 
                color: #666; 
            }
            .branch-detail strong { 
                color: #333; 
            }
            .main-index { 
                background: white; 
                border-radius: 8px; 
                padding: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            }
            .main-index h2 { 
                margin-top: 0; 
                color: #333; 
                display: flex; 
                align-items: center; 
            }
            .main-index h2 .icon { 
                margin-right: 10px; 
            }
            .chain-item { 
                background: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 5px; 
                padding: 15px; 
                margin-bottom: 10px; 
                cursor: pointer; 
                transition: all 0.3s ease; 
            }
            .chain-item:hover { 
                background: #e9ecef; 
                transform: translateY(-2px); 
                box-shadow: 0 4px 8px rgba(0,0,0,0.1); 
            }
            .chain-name { 
                font-weight: bold; 
                font-size: 16px; 
                margin-bottom: 5px; 
                color: #333; 
            }
            .chain-url { 
                color: #666; 
                font-size: 14px; 
                word-break: break-all; 
            }
            .phase-controls { 
                background: white; 
                border-radius: 8px; 
                padding: 20px; 
                margin-bottom: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            }
            .phase-btn { 
                background: #007bff; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                border-radius: 5px; 
                margin: 5px; 
                cursor: pointer; 
                font-size: 14px; 
                transition: background 0.3s ease; 
            }
            .phase-btn:hover { 
                background: #0056b3; 
            }
            .status { 
                background: white; 
                border-radius: 8px; 
                padding: 15px; 
                margin-bottom: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>
                <span class="icon">🏗️</span>
                Hierarchical Food Chain Database
            </h1>
            <div class="nav-path">Navigate: Main Index → Food Chains → Branches → Products</div>
        </div>
        
        <div class="container">
            <div class="status" id="status">
                Loading database status...
            </div>
            
            <div class="phase-controls">
                <button class="phase-btn" onclick="runPhase(1)">Run Phase 1 - Discover Food Chains</button>
                <button class="phase-btn" onclick="runPhase(2)">Run Phase 2 - Discover Branches</button>
                <button class="phase-btn" onclick="runPhase(3)">Run Phase 3 - Download Files</button>
                <button class="phase-btn" onclick="updateFileNames()">Update File Names</button>
                <button class="phase-btn" onclick="runUpdate()" style="background: #28a745; font-weight: bold;">🔄 Update Database</button>
                <button class="phase-btn" onclick="loadMainIndex()">Refresh Data</button>
            </div>
            
            <div id="content">
                Loading content...
            </div>
        </div>
        
        <script>
            let currentView = 'main-index';
            let currentChainCode = null;
            
            async function loadStatus() {
                try {
                    const response = await fetch('/status');
                    const status = await response.json();
                    document.getElementById('status').innerHTML = `
                        <strong>Database Status:</strong><br>
                        Exists: ${status.exists}<br>
                        Food Chains: ${status.food_chains}<br>
                        Total Branches: ${status.total_branches}
                    `;
                } catch (error) {
                    document.getElementById('status').innerHTML = 'Error loading status: ' + error;
                }
            }
            
            async function loadMainIndex() {
                currentView = 'main-index';
                currentChainCode = null;
                
                try {
                    const response = await fetch('/food-chains');
                    const data = await response.json();
                    
                    let html = `
                        <div class="breadcrumbs">
                            <div class="breadcrumb-path">
                                <div class="breadcrumb-item">
                                    <span class="icon">🏠</span>
                                    Main Index
                                </div>
                            </div>
                        </div>
                        
                        <div class="main-index">
                            <h2><span class="icon">🏢</span> Food Chains</h2>
                    `;
                    
                    if (data.food_chains && data.food_chains.length > 0) {
                        for (const chain of data.food_chains) {
                            html += `
                                <div class="chain-item" onclick="loadChainBranches('${chain.code}')">
                                    <div class="chain-name">${chain.name} (${chain.code})</div>
                                    <div class="chain-url">${chain.url}</div>
                                </div>
                            `;
                        }
                    } else {
                        html += '<p>No food chains found. Run Phase 1 to discover food chains.</p>';
                    }
                    
                    html += '</div>';
                    document.getElementById('content').innerHTML = html;
                } catch (error) {
                    document.getElementById('content').innerHTML = 'Error loading data: ' + error;
                }
            }
            
            async function loadChainBranches(chainCode) {
                currentView = 'chain-branches';
                currentChainCode = chainCode;
                
                try {
                    const [chainsResponse, branchesResponse] = await Promise.all([
                        fetch('/food-chains'),
                        fetch(`/branches/${chainCode}`)
                    ]);
                    
                    const chainsData = await chainsResponse.json();
                    const branchesData = await branchesResponse.json();
                    
                    const chain = chainsData.food_chains.find(c => c.code === chainCode);
                    
                    let html = `
                        <div class="breadcrumbs">
                            <div class="breadcrumb-path">
                                <div class="breadcrumb-item">
                                    <span class="icon">🏠</span>
                                    Main Index
                                </div>
                                <span>→</span>
                                <div class="breadcrumb-item">
                                    <span class="icon">🏢</span>
                                    ${chainCode}
                                </div>
                            </div>
                            <button class="back-btn" onclick="loadMainIndex()">← Back to Main Index</button>
                        </div>
                        
                        <div class="chain-header">
                            <h1 class="chain-title">
                                <span class="icon">🏢</span>
                                ${chainCode}: ${chain.name}
                            </h1>
                        </div>
                        
                        <div class="metadata-section">
                            <div class="metadata-title">
                                <span class="icon">🏢</span>
                                Chain Metadata
                            </div>
                            <div class="metadata-grid">
                                <div class="metadata-item">
                                    <div class="metadata-label">Chain Name</div>
                                    <div class="metadata-value">${chain.name}</div>
                                </div>
                                <div class="metadata-item">
                                    <div class="metadata-label">Chain URL</div>
                                    <div class="metadata-value">${chain.url}</div>
                                </div>
                                <div class="metadata-item">
                                    <div class="metadata-label">Total Branches</div>
                                    <div class="metadata-value">${branchesData.branches ? branchesData.branches.length : 0}</div>
                                </div>
                                <div class="metadata-item">
                                    <div class="metadata-label">Last Update</div>
                                    <div class="metadata-value">${new Date().toISOString()}</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="branches-section">
                            <div class="branches-title">
                                <span class="icon">🏢</span>
                                Branches
                            </div>
                    `;
                    
                    if (branchesData.branches && branchesData.branches.length > 0) {
                        for (const branch of branchesData.branches) {
                            html += `
                                <div class="branch-item" onclick="loadBranchDetails('${chainCode}', '${branch.code}')" style="cursor:pointer;">
                                    <div class="branch-header">Branch ${branch.code}: ${branch.name}</div>
                                    <div class="branch-details">
                                        <div class="branch-detail">
                                            <strong>Price File:</strong> ${branch.price_file || 'N/A'}
                                        </div>
                                        <div class="branch-detail">
                                            <strong>Promo File:</strong> ${branch.promo_file || 'N/A'}
                                        </div>
                                    </div>
                                </div>
                            `;
                        }
                    } else {
                        html += `
                            <div style="text-align: center; padding: 40px; color: #666;">
                                <div style="font-size: 48px; margin-bottom: 20px;">🏢</div>
                                <h3 style="margin-bottom: 15px; color: #333;">No Branches Available Yet</h3>
                                <p style="margin-bottom: 25px; font-size: 16px;">
                                    This food chain hasn't been processed yet. The server needs to discover and populate the branch information.
                                </p>
                                <p style="font-size: 14px; color: #888;">
                                    Run Phase 2 to discover branches for this food chain.
                                </p>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                    document.getElementById('content').innerHTML = html;
                } catch (error) {
                    document.getElementById('content').innerHTML = `
                        <div class="breadcrumbs">
                            <div class="breadcrumb-path">
                                <div class="breadcrumb-item">
                                    <span class="icon">🏠</span>
                                    Main Index
                                </div>
                                <span>→</span>
                                <div class="breadcrumb-item">
                                    <span class="icon">🏢</span>
                                    ${chainCode}
                                </div>
                            </div>
                            <button class="back-btn" onclick="loadMainIndex()">← Back to Main Index</button>
                        </div>
                        
                        <div style="text-align: center; padding: 40px; color: #666;">
                            <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
                            <h3 style="margin-bottom: 15px; color: #333;">Error Loading Chain Data</h3>
                            <p style="margin-bottom: 25px; font-size: 16px;">
                                There was an error loading the branch information for this food chain.
                            </p>
                            <p style="font-size: 14px; color: #888;">
                                Error: ${error}
                            </p>
                        </div>
                    `;
                }
            }

            async function loadBranchDetails(chainCode, branchCode) {
                try {
                    const [chainsResponse, branchResponse] = await Promise.all([
                        fetch('/food-chains'),
                        fetch(`/branch/${chainCode}/${branchCode}`)
                    ]);
                    const chainsData = await chainsResponse.json();
                    const branchData = await branchResponse.json();
                    const chain = chainsData.food_chains.find(c => c.code === chainCode);
                    const b = branchData.branch || { code: branchCode, name: 'Unknown' };

                    let html = `
                        <div class="breadcrumbs">
                            <div class="breadcrumb-path">
                                <div class="breadcrumb-item"><span class="icon">🏠</span>Main Index</div>
                                <span>→</span>
                                <div class="breadcrumb-item"><span class="icon">🏢</span>${chainCode}</div>
                                <span>→</span>
                                <div class="breadcrumb-item"><span class="icon">🏬</span>Branch ${b.code}</div>
                            </div>
                            <button class="back-btn" onclick="loadChainBranches('${chainCode}')">← Back to ${chainCode}</button>
                        </div>

                        <div class="chain-header">
                            <h1 class="chain-title"><span class="icon">🏬</span> Branch ${b.code}: ${b.name}</h1>
                        </div>

                        <div class="metadata-section">
                            <div class="metadata-title"><span class="icon">ℹ️</span> Branch Metadata</div>
                            <div class="metadata-grid">
                                <div class="metadata-item"><div class="metadata-label">Chain Name</div><div class="metadata-value">${chain.name}</div></div>
                                <div class="metadata-item"><div class="metadata-label">Chain URL</div><div class="metadata-value">${chain.url}</div></div>
                                <div class="metadata-item"><div class="metadata-label">Latest Price File</div><div class="metadata-value">${b.price_file || 'N/A'}</div></div>
                                <div class="metadata-item"><div class="metadata-label">Latest Promo File</div><div class="metadata-value">${b.promo_file || 'N/A'}</div></div>
                            </div>
                        </div>

                        <div class="branches-section">
                            <div class="branches-title"><span class="icon">🧭</span> View</div>
                            <div style="margin-bottom:15px;">
                                <button id="tab-products" class="phase-btn" onclick="renderBranchProducts('${chainCode}','${branchCode}')">Products</button>
                                <button id="tab-promotions" class="phase-btn" onclick="renderBranchPromotions('${chainCode}','${branchCode}')">Promotions</button>
                            </div>
                            <div id="branch-content"></div>
                        </div>
                    `;

                    document.getElementById('content').innerHTML = html;
                    window.__branchCache = branchData;
                    renderBranchProducts(chainCode, branchCode);
                } catch (error) {
                    alert('Error loading branch details: ' + error);
                }
            }

            function renderBranchProducts(chainCode, branchCode) {
                const data = window.__branchCache || { products: [] };
                let inner = '';
                if (data.products && data.products.length > 0) {
                    document.getElementById('tab-products').style.background = '#0056b3';
                    document.getElementById('tab-promotions').style.background = '#007bff';
                    for (const p of data.products) {
                        inner += `
                            <div class="branch-item">
                                <div class="branch-header">${p.item_name || '(no name)'}</div>
                                <div class="branch-details">
                                    <div class="branch-detail"><strong>Code:</strong> ${p.item_code || ''}</div>
                                    <div class="branch-detail"><strong>Price:</strong> ${p.item_price}</div>
                                    <div class="branch-detail"><strong>Manufacturer:</strong> ${p.manufacturer_name || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Unit:</strong> ${p.unit_of_measure || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Quantity:</strong> ${p.quantity || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Updated:</strong> ${p.price_update_date || 'N/A'}</div>
                                </div>
                            </div>
                        `;
                    }
                } else {
                    inner = '<p>No products found for this branch.</p>';
                }
                document.getElementById('branch-content').innerHTML = inner;
            }

            function renderBranchPromotions(chainCode, branchCode) {
                const data = window.__branchCache || { promotions: [] };
                let inner = '';
                if (data.promotions && data.promotions.length > 0) {
                    document.getElementById('tab-products').style.background = '#007bff';
                    document.getElementById('tab-promotions').style.background = '#0056b3';
                    for (const pr of data.promotions) {
                        inner += `
                            <div class="branch-item">
                                <div class="branch-header">${pr.promotion_description || 'Promotion'}</div>
                                <div class="branch-details">
                                    <div class="branch-detail"><strong>ID:</strong> ${pr.promotion_id || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Discounted Price:</strong> ${pr.discounted_price || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Per Unit:</strong> ${pr.discounted_price_per_unit || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Min Qty:</strong> ${pr.min_quantity || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Max Qty:</strong> ${pr.max_quantity || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Start:</strong> ${pr.promotion_start_date || 'N/A'}</div>
                                    <div class="branch-detail"><strong>End:</strong> ${pr.promotion_end_date || 'N/A'}</div>
                                    <div class="branch-detail"><strong>Items:</strong> ${pr.item_count || 0}</div>
                                    <div class="branch-detail" style="grid-column: 1 / -1; word-break: break-all;">
                                        <strong>Item Codes:</strong> ${(pr.item_codes && pr.item_codes.length ? pr.item_codes.join(', ') : 'N/A')}
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                } else {
                    inner = '<p>No promotions found for this branch.</p>';
                }
                document.getElementById('branch-content').innerHTML = inner;
            }
            
            async function runPhase(phase) {
                try {
                    const response = await fetch(`/phase${phase}`);
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        alert(`Phase ${phase} completed successfully!`);
                        loadStatus();
                        if (currentView === 'main-index') {
                            loadMainIndex();
                        } else if (currentView === 'chain-branches' && currentChainCode) {
                            loadChainBranches(currentChainCode);
                        }
                    } else {
                        alert(`Phase ${phase} failed: ${result.error}`);
                    }
                } catch (error) {
                    alert(`Error running phase ${phase}: ${error}`);
                }
            }
            
            async function updateFileNames() {
                try {
                    const response = await fetch('/update-file-names');
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        alert(`File names updated successfully! Total updates: ${result.total_updates}`);
                        loadStatus();
                        if (currentView === 'main-index') {
                            loadMainIndex();
                        } else if (currentView === 'chain-branches' && currentChainCode) {
                            loadChainBranches(currentChainCode);
                        }
                    } else {
                        alert(`File name update failed: ${result.error}`);
                    }
                } catch (error) {
                    alert(`Error updating file names: ${error}`);
                }
            }
            
            async function runUpdate() {
                try {
                    const response = await fetch('/update');
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        alert(`Database update completed successfully!\\nFile updates: ${result.file_updates}\\nItems processed: ${result.items_processed}`);
                        loadStatus();
                        if (currentView === 'main-index') {
                            loadMainIndex();
                        } else if (currentView === 'chain-branches' && currentChainCode) {
                            loadChainBranches(currentChainCode);
                        }
                    } else {
                        alert(`Database update failed: ${result.error}`);
                    }
                } catch (error) {
                    alert(`Error running database update: ${error}`);
                }
            }
            
            // Load initial data
            loadStatus();
            loadMainIndex();
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    log_message("🚀 Starting Food Chain Data Server...")
    ensure_data_directory()
    
    log_message("🌐 Server will be available at: http://localhost:5000")
    log_message("📋 Available endpoints:")
    log_message("   - GET / (home)")
    log_message("   - GET /status (database status)")
    log_message("   - GET /phase1 (discover food chains)")
    log_message("   - GET /phase2 (discover branches)")
    log_message("   - GET /phase3 (download files)")
    log_message("   - GET /food-chains (all food chains)")
    log_message("   - GET /branches/<chain_code> (branches for chain)")
    log_message("   - GET /viewer (web interface)")
    log_message("🔄 Server ready!")
    
    app.run(host='0.0.0.0', port=5000, debug=False) 