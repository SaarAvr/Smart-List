# 🛒 Smart Shared List

**Israeli Food Chain Price Comparison System**

A comprehensive system for scraping, storing, and comparing food prices across Israeli supermarket chains. Built with Python Flask backend and Flutter mobile app.

## 🎯 **Project Overview**

This system automatically downloads and processes price data from the Israeli government's food price transparency website, creating a hierarchical database structure for efficient price comparison and shopping list optimization.

## 🏗️ **Architecture**

### **Backend (Python/Flask)**
- **Web Scraping**: Selenium-based automation for downloading PriceFull and PromoFull files
- **Data Processing**: XML parsing and hierarchical database storage
- **API**: RESTful endpoints for data access and comparison
- **Database**: SQLite with dynamic table creation for scalability

### **Frontend (Flutter)**
- **Mobile App**: Cross-platform shopping list management
- **Firebase Integration**: User authentication and data synchronization
- **Price Comparison**: Real-time price optimization across chains

## 📊 **Database Structure**

```
Main Index
├── Food Chain Tables (chain_XXX_branches)
│   ├── Branch Tables (branch_XXX_YYY_products)
│   ├── Branch Tables (branch_XXX_YYY_promotions)
│   └── Branch Tables (branch_XXX_YYY_promotion_items)
└── Metadata Tables
```

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.10+
- Flutter SDK
- Chrome/Chromium browser (for Selenium)

### **Backend Setup**
```bash
# Clone repository
git clone https://github.com/SaarAvr/Smart-List.git
cd Smart-List

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask selenium webdriver-manager requests

# Run the server
python3 app.py
```

### **API Endpoints**
- `GET /hierarchical-overview` - Database overview
- `GET /hierarchical-chain/<chain_code>` - Chain branches
- `GET /hierarchical-branch/<chain_code>/<branch_code>` - Branch products/promotions
- `GET /hierarchical-viewer` - Interactive database viewer

### **Flutter Setup**
```bash
# Install Flutter dependencies
flutter pub get

# Run the app
flutter run
```

## 📈 **Current Status**

### **✅ Completed**
- [x] Web scraping infrastructure (Selenium)
- [x] Hierarchical database design
- [x] PriceFull file processing (6,338+ products)
- [x] PromoFull file processing (642+ promotions)
- [x] Interactive database viewer
- [x] API endpoints for data access

### **🔄 In Progress**
- [ ] Price comparison algorithms
- [ ] Shopping list optimization
- [ ] Multi-chain scaling (29 chains discovered)

### **📋 Planned**
- [ ] Flutter app integration
- [ ] Real-time price updates
- [ ] User authentication
- [ ] Push notifications

## 🗂️ **Project Structure**

```
smart_shared_list/
├── app.py                          # Main Flask application
├── database_hierarchical.py        # Database management
├── database_setup.py              # Legacy database setup
├── hierarchical_viewer.html       # Interactive database viewer
├── data/                          # Database files
├── downloads/                     # Downloaded price files
├── lib/                          # Flutter app source
└── venv/                         # Python virtual environment
```

## 🔧 **Configuration**

### **Environment Variables**
Create a `.env` file:
```env
FLASK_ENV=development
FLASK_DEBUG=1
```

### **Database**
- **Location**: `data/hierarchical_food_chains.db`
- **Viewer**: Access via `http://localhost:5000/hierarchical-viewer`

## 📊 **Data Sources**

- **Government Website**: [Israeli Food Price Transparency](https://www.gov.il/he/pages/cpfta_prices_regulations)
- **File Types**: PriceFull (products) and PromoFull (promotions)
- **Format**: XML files compressed as .gz (actually ZIP format)

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- Israeli government for providing open price data
- Selenium community for web automation tools
- Flutter team for cross-platform development framework

---

**Built with ❤️ for smarter shopping in Israel**
