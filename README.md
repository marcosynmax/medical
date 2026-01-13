# CMS Rates

A Python tool for looking up Medicare Physician Fee Schedule reimbursement rates by CPT code and geographic region. Includes both a CLI and a web-based GUI.

## Features

- Look up Medicare reimbursement rates by CPT/HCPCS code and state/locality
- **Multi-code batch lookup** with summary table and total payment
- **Multi-payer rate comparison** - Compare Medicare rates with commercial insurers and Medicaid
- Support for facility and non-facility rates
- Web-based GUI for easy lookups
- CLI with multiple output formats: table, JSON, CSV
- Verbose mode showing calculation breakdown
- Downloads official CMS RVU data files
- Covers all 50 states with 90+ locality-specific GPCI adjustments

## Installation

### Requirements

- Python 3.9+
- pip

### Install dependencies

```bash
cd medical
pip install click rich httpx pydantic streamlit
```

### Download CMS data

Before using the tool, download the fee schedule data:

```bash
PYTHONPATH=src python3 -m cms_rates update
```

This downloads ~18,000 CPT codes and GPCI data for all localities.

## Web GUI

Launch the web-based graphical interface:

```bash
PYTHONPATH=src streamlit run src/cms_rates/app.py
```

Then open http://localhost:8501 in your browser.

The GUI provides:
- Single code lookup with detailed breakdown
- **Multi-code batch lookup** with summary table and total payment
- Search CPT codes by description
- **Rate comparison** across Medicare, commercial insurers, and Medicaid
- State/region dropdown selector
- Facility/non-facility toggle
- Calculation breakdown display
- View all localities in a state
- Add and manage payer rates directly in the UI

## CLI Usage

### Basic lookup

```bash
# Look up rate for CPT 99213 in California
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r CA

# Use full state name
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r California

# Look up facility rate
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r CA --facility
```

### Multi-code lookup

```bash
# Look up multiple codes at once
PYTHONPATH=src python3 -m cms_rates lookup 99213 99214 99215 -r CA

# Get total payment for a procedure set
PYTHONPATH=src python3 -m cms_rates lookup 99213 99214 99215 -r TX --facility

# Output as JSON
PYTHONPATH=src python3 -m cms_rates lookup 99213 99214 -r NY --format json
```

### Output formats

```bash
# JSON output
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r CA --format json

# CSV output
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r TX --format csv

# Verbose output with calculation breakdown
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r NY --verbose
```

### View all localities in a state

```bash
# Show rates for all California localities
PYTHONPATH=src python3 -m cms_rates lookup 99213 -r CA --all-localities
```

### List available localities

```bash
# List all localities
PYTHONPATH=src python3 -m cms_rates list-localities

# Filter by state
PYTHONPATH=src python3 -m cms_rates list-localities --state TX
```

### Get CPT code information

```bash
PYTHONPATH=src python3 -m cms_rates info 99213
```

### Search by description

```bash
# Search for CPT codes by description
PYTHONPATH=src python3 -m cms_rates search "office visit"

# Search with more results
PYTHONPATH=src python3 -m cms_rates search "x-ray" --limit 50

# Search with JSON output
PYTHONPATH=src python3 -m cms_rates search "MRI" --format json
```

### Payer rate comparison

Compare Medicare rates with commercial insurers and Medicaid:

```bash
# Compare rates for a CPT code across all payers
PYTHONPATH=src python3 -m cms_rates compare 99213 -r CA

# Compare facility rates
PYTHONPATH=src python3 -m cms_rates compare 99213 -r CA --facility

# Output as JSON
PYTHONPATH=src python3 -m cms_rates compare 99213 -r TX --format json
```

### Add payer rates

```bash
# Add a fixed rate for a payer
PYTHONPATH=src python3 -m cms_rates add-payer-rate 99213 "Blue Cross CA" --rate 115.50 --state CA

# Add rate as percentage of Medicare
PYTHONPATH=src python3 -m cms_rates add-payer-rate 99213 "Aetna" --percent-medicare 120 --type commercial

# Add Medicaid rate
PYTHONPATH=src python3 -m cms_rates add-payer-rate 99213 "Medi-Cal" --rate 72.00 --state CA --type medicaid

# Add with facility and non-facility rates
PYTHONPATH=src python3 -m cms_rates add-payer-rate 99213 "Cigna" --rate 110.00 --facility-rate 85.00 --state CA
```

### Import payer rates from CSV

```bash
# Import rates from a CSV file
PYTHONPATH=src python3 -m cms_rates import-payer-rates medicaid_rates.csv --payer "Medi-Cal" --state CA --type medicaid

# Preview import without saving (dry run)
PYTHONPATH=src python3 -m cms_rates import-payer-rates rates.csv --payer "BCBS" --dry-run

# Custom column names
PYTHONPATH=src python3 -m cms_rates import-payer-rates data.csv --payer "Aetna" --code-column "CPT" --rate-column "Amount"
```

### Manage payers

```bash
# List all payers in the database
PYTHONPATH=src python3 -m cms_rates list-payers

# List payers as JSON
PYTHONPATH=src python3 -m cms_rates list-payers --format json

# Delete payer rates
PYTHONPATH=src python3 -m cms_rates delete-payer "Old Payer" --confirm
```

## Example Output

```
$ PYTHONPATH=src python3 -m cms_rates lookup 99213 -r CA --verbose

╭──────────────────────────────────────────────────────────────────╮
│ Medicare Physician Fee Schedule - CPT 99213                      │
╰──────────────────────────────────────────────────────────────────╯
  Code:           99213
  Description:    Office o/p est low 20 min
  Year:           2025
  Setting:        Non-Facility
  Locality:       Rest of California (01182-99)
  Payment:        $90.16

           Calculation Breakdown
 Component            RVU   GPCI  Adjusted
 Work                1.30  1.014    1.3182
 Practice Expense    1.35  1.035    1.3973
 Malpractice         0.10  0.718    0.0718
                                  ────────
 Total Adjusted RVU                 2.7873

Conversion Factor: $32.3465
Final Payment: $2.7873 × $32.3465 = $90.16
```

### Rate Comparison Example

```
$ PYTHONPATH=src python3 -m cms_rates compare 99213 -r CA

╭──────────────────────────────────────────────────────────────────────────────╮
│ Rate Comparison - CPT 99213 (Non-Facility)                                   │
│ Region: Anaheim/Santa Ana, CA (CA)                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Payer            ┃ Type       ┃    Rate ┃ % of Medicare ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Medicare (CMS)   │ government │  $99.65 │        100.0% │
│ Aetna            │ commercial │ $109.61 │        110.0% │
│ Blue Shield CA   │ commercial │ $114.60 │        115.0% │
│ Medi-Cal         │ medicaid   │  $72.00 │         72.3% │
│ UnitedHealthcare │ commercial │ $105.50 │        105.9% │
└──────────────────┴────────────┴─────────┴───────────────┘
```

## Commands

| Command | Description |
|---------|-------------|
| `lookup <CPT...> -r <REGION>` | Look up reimbursement rate (supports multiple codes) |
| `search <QUERY>` | Search CPT codes by description |
| `compare <CPT> -r <REGION>` | Compare Medicare rate with other payers |
| `add-payer-rate <CPT> <PAYER>` | Add a payer-specific rate |
| `import-payer-rates <CSV>` | Import payer rates from CSV file |
| `list-payers` | List all payers in the database |
| `delete-payer <PAYER>` | Delete rates for a payer |
| `update` | Download/update CMS fee schedule data |
| `list-localities` | List all available localities |
| `info <CPT>` | Show CPT code details without pricing |

## Options

### lookup command

| Option | Description |
|--------|-------------|
| `--region, -r` | State name, abbreviation, or locality code (required) |
| `--year, -y` | Fee schedule year (default: 2025) |
| `--facility, -f` | Show facility rate (default: non-facility) |
| `--modifier, -m` | Modifier code (TC, 26, etc.) |
| `--format, -o` | Output format: table, json, csv |
| `--all-localities` | Show rates for all localities in region |
| `--verbose, -v` | Show calculation breakdown |

Note: Multiple CPT codes can be provided as arguments for batch lookup.

## Data Sources

- **RVU Data**: [CMS Physician Fee Schedule Relative Value Files](https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files)
- **GPCI Data**: Geographic Practice Cost Indices by locality

## Payment Calculation

Medicare payment is calculated using the formula:

```
Payment = [(Work_RVU × Work_GPCI) + (PE_RVU × PE_GPCI) + (MP_RVU × MP_GPCI)] × Conversion_Factor
```

Where:
- **Work RVU**: Physician work component
- **PE RVU**: Practice expense (facility or non-facility)
- **MP RVU**: Malpractice component
- **GPCI**: Geographic Practice Cost Index for the locality
- **Conversion Factor**: $32.3465 (2025)

## License

MIT
