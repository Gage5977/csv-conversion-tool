# CSV Conversion Tool (WORKING)

A comprehensive Python-based system that replicates the functionality of the Excel Trial Balance Conversion Tool. This system transforms Bitwise trial balance data into MRI-compatible import files with sophisticated account mapping, validation, and reconciliation capabilities.

## 🎯 Features

### Core Functionality
- **Account Mapping Engine**: Transforms Bitwise account codes to MRI format using configurable mapping rules
- **MRI Import Generation**: Creates MRI-compatible CSV files with all required fields
- **Comprehensive Validation**: Multi-level validation framework replicating Excel validation sheets
- **File Format Support**: Handles both CSV and Excel trial balance files
- **Period-over-Period Activity**: Calculates account activity (Current - Prior) with materiality filtering

### Advanced Capabilities
- **Pattern Matching**: Regex-based account transformation rules
- **Consolidation Logic**: Special handling for retained earnings and other complex accounts
- **Variance Reporting**: Reconciliation between operator and system balances
- **Data Quality Checks**: Validation of data completeness and accuracy
- **Audit Trail**: Complete processing history and validation results

## 🏗️ Architecture

```
CSV-Conversion-Tool-WORKING/
├── app.py                          # Flask web application
├── requirements.txt                # Python dependencies
├── config/
│   └── system_config.json         # System configuration
├── data/mappings/
│   ├── gl_mapping.json            # Account mapping rules
│   └── mri_chart_of_accounts.json # Target chart of accounts
├── src/
│   ├── core/
│   │   └── enhanced_trial_balance_processor.py
│   ├── engines/
│   │   ├── account_mapping_engine.py
│   │   └── mri_import_generator.py
│   └── validators/
│       └── validation_engine.py
├── templates/
│   └── index.html                 # Web interface
├── static/                        # CSS/JS assets
├── logs/                         # Application logs
└── temp/                         # Temporary file storage
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation
1. **Clone or download the system**
   ```bash
   cd MRI_Trial_Balance_Import_System
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the web interface**
   - Open browser to `http://localhost:5000`

## 💻 Usage

### Web Interface
1. **Upload Files**: Upload prior and current period trial balance files (CSV or Excel)
2. **Configure Processing**: Set period (MM/YY format) and entity ID
3. **Process**: Click "Generate MRI Import File" to start processing
4. **Review Results**: View validation results and processing summary
5. **Download**: Download the generated MRI import CSV file

### API Endpoints
- `POST /api/process` - Process trial balances
- `GET /api/download/mri_import/<session_id>` - Download generated file
- `POST /api/validate` - Validate file format
- `GET /api/mappings` - Get account mappings
- `GET /api/config` - Get system configuration

## 📊 Data Formats

### Input (Trial Balance)
**CSV Format:**
```csv
Account,Description,Debit,Credit,Net
10100-0-000,Cash - Checking,1000.00,0.00,1000.00
81000,Scheduled Rent,0.00,5000.00,-5000.00
```

**Excel Format:**
- Automatically detects trial balance data within Excel files
- Supports various column naming conventions
- Handles metadata headers and complex formatting

### Output (MRI Import)
```csv
PERIOD,REF,SOURCE,ENTITYID,ACCTNUM,DEPARTMENT,AMT,DESCRPN,ENTRDATE,STATUS,BASIS,AUDITFLAG,ADDLDESC,ASSETCLASS,ASSETCODE,INTERENTITY
04/25,,GA,M55020,GM10100,@,-1765.39,Cash - Checking,2025-04-30 00:00:00,P,B,,,,,
04/25,,GA,M55020,GM81000,@,-5000.00,Scheduled Rent,2025-04-30 00:00:00,P,B,,,,,
```

## ⚙️ Configuration

### System Configuration (`config/system_config.json`)
```json
{
  "entity_config": {
    "default_entity_id": "M55020",
    "entity_name": "627 W Main St. - Merced, CA",
    "default_department": "@"
  },
  "processing_rules": {
    "materiality_threshold": 0.01,
    "zero_activity_exclude": true,
    "period_format": "MM/YY"
  },
  "mri_defaults": {
    "source": "GA",
    "status": "P",
    "basis": "B"
  }
}
```

### Account Mappings (`data/mappings/gl_mapping.json`)
```json
{
  "account_mappings": {
    "10100-0-000": {
      "target_account": "GM10100",
      "description": "Cash - Checking",
      "account_type": "Asset"
    }
  },
  "transformation_rules": {
    "remove_patterns": ["-0-000", ": .*"],
    "prefix_rules": {
      "default_prefix": "GM"
    }
  }
}
```

## 🔍 Validation Framework

The system includes comprehensive validation that replicates Excel validation sheets:

### Pre-Import Validations
1. **Account Mapping Validation**: Ensures all accounts have proper mappings
2. **Balance Reconciliation**: Validates Prior + Activity = Current
3. **Activity Calculation**: Verifies mathematical accuracy
4. **Materiality Threshold**: Applies filtering rules
5. **Data Quality**: Checks for completeness and consistency

### Validation Results
- **PASS**: All validations successful
- **FAIL**: Critical validations failed
- **WARNING**: Non-critical issues detected

## 📈 Processing Workflow

1. **File Upload & Parsing**
   - Support for CSV and Excel formats
   - Automatic format detection
   - Data cleaning and standardization

2. **Account Mapping**
   - Apply transformation rules
   - Pattern matching for complex accounts
   - Consolidation logic for special cases

3. **Activity Calculation**
   - Period-over-period comparison
   - Materiality threshold application
   - Zero-activity filtering

4. **MRI Import Generation**
   - Format to exact MRI specifications
   - Apply default values and business rules
   - Generate all required fields

5. **Validation & Export**
   - Comprehensive validation suite
   - Variance analysis and reconciliation
   - CSV export with proper formatting

## 🛠️ Customization

### Adding New Account Mappings
Edit `data/mappings/gl_mapping.json`:
```json
{
  "account_mappings": {
    "NEW-ACCOUNT": {
      "target_account": "GM12345",
      "description": "New Account Description",
      "account_type": "Asset"
    }
  }
}
```

### Modifying Validation Rules
Edit `config/system_config.json`:
```json
{
  "validation_rules": {
    "require_account_mapping": true,
    "validate_balance_reconciliation": true,
    "check_materiality_threshold": true
  }
}
```

### Adjusting Processing Rules
```json
{
  "processing_rules": {
    "materiality_threshold": 0.01,
    "rounding_precision": 2,
    "balance_tolerance": 0.005
  }
}
```

## 🔧 Troubleshooting

### Common Issues

**File Upload Errors**
- Ensure files are in CSV or Excel format
- Check for proper column headers
- Verify numeric data formatting

**Mapping Errors**
- Review unmapped accounts in validation results
- Add missing mappings to `gl_mapping.json`
- Check transformation rules

**Validation Failures**
- Review specific validation error messages
- Check data consistency between prior and current periods
- Verify account mappings are complete

### Log Files
Application logs are stored in `logs/mri_import_system.log` for debugging.

## 📄 License

This system replicates proprietary Excel functionality for internal use. Ensure compliance with your organization's software policies.

## 🤝 Support

For questions or issues:
1. Review the validation results for specific error messages
2. Check the application logs for detailed error information
3. Verify configuration files are properly formatted
4. Ensure all required account mappings are defined

## 🔄 Version History

**v1.0.0** - Initial release
- Complete Excel functionality replication
- Web-based interface
- Comprehensive validation framework
- MRI import file generation
- Automatic journal entry generation
- Download journal entries in CSV format
- AI assistant for help and guidance
- Dark mode interface

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher (for local development)
- Modern web browser

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/finance-etl-interface.git
cd finance-etl-interface
```

2. Create a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask backend:
```bash
python app.py
```

2. Open `finance-etl-interface.html` in your web browser

3. Upload your trial balance files:
   - Prior period trial balance (CSV)
   - Current period trial balance (CSV)

4. Click "Process Files" to generate journal entries

5. Download the generated journal entries CSV

## CSV File Format

Trial balance files should be in CSV format with the following columns:
- Account: Account number/code
- Description: Account description
- Debit: Debit amount (numeric)
- Credit: Credit amount (numeric)

Example:
```csv
Account,Description,Debit,Credit
1000,Cash,5000.00,0.00
2000,Accounts Payable,0.00,3000.00
```

## Development

The project consists of three main components:

1. `trial_balance_processor.py`: Core processing logic
2. `app.py`: Flask API backend
3. `finance-etl-interface.html`: Web interface

### Backend API Endpoints

- `POST /api/validate`: Validate CSV file structure
- `POST /api/process`: Process trial balance files
- `GET /api/download/journal_entries`: Download generated journal entries

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the development team.
