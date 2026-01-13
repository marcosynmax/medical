# Medicare Rate Comparison Tool

A web-based application for looking up CMS Medicare reimbursement rates and comparing them with commercial insurance and Medicaid fee schedules.

## Features

- **Medicare Rate Lookup** - Search 2026 CMS Physician Fee Schedule rates by CPT/HCPCS code, state, and locality
- **Rate Comparison** - Side-by-side comparison of Medicare vs custom payer rates
- **Data Import** - Import CMS Payment Amount files and custom CSV fee schedules
- **Payer Management** - View, manage, and delete imported payer data

## Installation

```bash
cd rate-compare
pip install -r requirements.txt
```

## Usage

### Start the Web GUI

```bash
PYTHONPATH=src streamlit run src/rate_compare/app.py
```

Open http://localhost:8501 in your browser.

### Import Medicare Data

1. Go to the **Import Data** tab
2. Select "Medicare Data (CMS)"
3. Upload a CMS Payment Amount file (PFALL26A format)
4. Click "Import Medicare Data"

### Import Custom Payer Rates

1. Go to the **Import Data** tab
2. Select "Custom Payer (CSV)"
3. Upload a CSV file with fee schedule data
4. Map CSV columns to required fields:
   - HCPCS Code column
   - Non-Facility Fee column
   - Facility Fee column (optional)
   - State column (optional)
5. Enter payer name and type
6. Click "Import Payer Data"

### CSV Format Example

```csv
hcpcs_code,modifier,fee,facility_fee,state
99213,,95.50,65.00,TX
99214,,125.00,85.00,TX
99215,,175.00,120.00,TX
```

## Project Structure

```
rate-compare/
├── src/
│   └── rate_compare/
│       ├── app.py              # Streamlit web GUI
│       ├── config.py           # Configuration settings
│       ├── db/
│       │   ├── database.py     # SQLite connection
│       │   └── schema.py       # Table definitions
│       ├── models/
│       │   ├── medicare.py     # Medicare rate model
│       │   └── payer.py        # Custom payer model
│       ├── parsers/
│       │   ├── cms_parser.py   # CMS file parser
│       │   └── csv_parser.py   # CSV fee schedule parser
│       └── services/
│           ├── lookup.py       # Medicare lookup service
│           └── compare.py      # Rate comparison service
├── requirements.txt
└── README.md
```

## Database

Data is stored in SQLite at `~/.rate-compare/rate_compare.db`

### Tables

- **medicare_rates** - CMS Medicare rates by code, carrier, and locality
- **payer_rates** - Custom payer fee schedules
- **localities** - Carrier/locality reference data

## Data Sources

### CMS Payment Amount Files

Download from [CMS Physician Fee Schedule](https://www.cms.gov/medicare/payment/fee-schedules/physician):
- PFALL26A - 2026 Payment Amount File
- Contains pre-calculated payment amounts by locality

### Custom Payers

Import any fee schedule as CSV with flexible column mapping:
- Commercial insurance (Blue Cross, Aetna, etc.)
- State Medicaid programs
- Custom/contracted rates

## License

MIT
