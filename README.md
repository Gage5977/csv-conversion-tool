# Finance ETL Interface

A web-based interface for processing trial balance data and generating journal entries. This system compares prior and current period trial balances to calculate activity and generate the necessary journal entries for importing into accounting systems.

## Features

- Upload prior and current period trial balances
- Automatic validation of CSV file structure
- Period-over-period activity calculation
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