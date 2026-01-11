# Sellence Lead Finder

Find companies that collect phone numbers on their websites — the key qualification signal for Sellence prospects.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate a list of companies in your target vertical
python find_companies.py --vertical insurance --output insurance_companies.csv

# 3. Check which ones have phone number fields
python lead_finder.py --input insurance_companies.csv --output qualified_leads.csv
```

## How It Works

### Step 1: Find Companies

```bash
# Insurance companies
python find_companies.py --vertical insurance --output insurance.csv

# Education companies (bootcamps, online courses)
python find_companies.py --vertical education --output education.csv

# Finance companies (neobanks, trading platforms)
python find_companies.py --vertical finance --output finance.csv

# Real estate / mortgage
python find_companies.py --vertical real_estate --output realestate.csv

# Premium e-commerce
python find_companies.py --vertical ecommerce --output ecommerce.csv

# All verticals at once
python find_companies.py --all-verticals --output all_companies.csv
```

**With Apollo.io API (more companies):**
```bash
python find_companies.py --vertical insurance --apollo-key YOUR_API_KEY --limit 100
```

### Step 2: Check for Phone Fields

```bash
# Process the CSV and find qualified leads
python lead_finder.py --input companies.csv --output qualified_leads.csv

# Check a single website
python lead_finder.py --url https://example.com
```

**Options:**
- `--url-column "Website"` - Specify the column name with website URLs
- `--workers 10` - Increase parallel workers for faster processing
- `--no-subpages` - Only check homepage (faster but less thorough)

## Output

The tool creates two files:
1. `qualified_leads.csv` - Companies WITH phone number fields (ready for outreach!)
2. `qualified_leads_all.csv` - All companies with check results

## What It Checks

The tool looks for phone number fields by checking:
- `<input type="tel">` elements
- Inputs with "phone", "mobile", "tel" in name/id/placeholder
- Form labels containing phone-related text
- Contact, quote, and demo pages (not just homepage)

## Adding Your Own Company Lists

Create a CSV with at least a `website` column:

```csv
company_name,website,industry
Lemonade,lemonade.com,Insurance
Root Insurance,root.com,Insurance
```

Then run:
```bash
python lead_finder.py --input your_companies.csv
```

## Pro Tips

1. **Start with sample lists** - The tool comes with 100+ pre-loaded companies across verticals
2. **Use Apollo for scale** - Get an Apollo.io API key to find thousands of companies
3. **Check multiple verticals** - Run `--all-verticals` to check all at once
4. **Export to Clay** - Import qualified leads into Clay for contact enrichment

## Next Steps After Finding Leads

1. Import `qualified_leads.csv` into Clay
2. Enrich with decision-maker contacts (VP Marketing, Head of Growth)
3. Find their email addresses
4. Launch your email campaign!
