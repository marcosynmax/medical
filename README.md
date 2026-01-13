# CMS Rates

A Python tool for looking up Medicare Physician Fee Schedule reimbursement rates by CPT code and geographic region. Includes both a CLI and a web-based GUI.

## Features

- Look up Medicare reimbursement rates by CPT/HCPCS code and state/locality
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
- CPT code input field
- State/region dropdown selector
- Facility/non-facility toggle
- Calculation breakdown display
- View all localities in a state

## CLI Usage

### Basic lookup

```bash
# Look up rate for CPT 99213 in California
PYTHONPATH=src python3 -m cms_rates lookup 99213 CA

# Use full state name
PYTHONPATH=src python3 -m cms_rates lookup 99213 California

# Look up facility rate
PYTHONPATH=src python3 -m cms_rates lookup 99213 CA --facility
```

### Output formats

```bash
# JSON output
PYTHONPATH=src python3 -m cms_rates lookup 99213 CA --format json

# CSV output
PYTHONPATH=src python3 -m cms_rates lookup 99213 TX --format csv

# Verbose output with calculation breakdown
PYTHONPATH=src python3 -m cms_rates lookup 99213 NY --verbose
```

### View all localities in a state

```bash
# Show rates for all California localities
PYTHONPATH=src python3 -m cms_rates lookup 99213 CA --all-localities
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

## Example Output

```
$ PYTHONPATH=src python3 -m cms_rates lookup 99213 CA --verbose

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

## Commands

| Command | Description |
|---------|-------------|
| `lookup <CPT> <REGION>` | Look up reimbursement rate |
| `search <QUERY>` | Search CPT codes by description |
| `update` | Download/update CMS fee schedule data |
| `list-localities` | List all available localities |
| `info <CPT>` | Show CPT code details without pricing |

## Options

### lookup command

| Option | Description |
|--------|-------------|
| `--year, -y` | Fee schedule year (default: 2025) |
| `--facility, -f` | Show facility rate (default: non-facility) |
| `--modifier, -m` | Modifier code (TC, 26, etc.) |
| `--format, -o` | Output format: table, json, csv |
| `--all-localities` | Show rates for all localities in region |
| `--verbose, -v` | Show calculation breakdown |

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
