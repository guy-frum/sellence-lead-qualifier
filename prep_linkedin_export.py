#!/usr/bin/env python3
"""
Prepare LinkedIn Sales Navigator export for lead checking.
Cleans up the data and extracts website URLs.
"""

import csv
import re
import argparse
from urllib.parse import urlparse

def clean_url(url):
    """Clean and normalize a URL."""
    if not url:
        return ''

    url = url.strip()

    # Remove common prefixes
    url = re.sub(r'^(https?://)?(www\.)?', '', url, flags=re.IGNORECASE)

    # Remove trailing slashes and paths
    url = url.split('/')[0]

    # Remove any remaining whitespace
    url = url.strip()

    return url

def process_linkedin_export(input_file, output_file):
    """Process LinkedIn Sales Navigator export."""

    companies = []
    seen_domains = set()

    # Try different possible column names for website
    website_columns = ['Website', 'website', 'Company Website', 'company_website', 'URL', 'url', 'Domain', 'domain']
    name_columns = ['Company', 'company', 'Company Name', 'company_name', 'Account Name', 'Name', 'name']
    industry_columns = ['Industry', 'industry', 'Company Industry']
    size_columns = ['Company Size', 'Employees', 'Employee Count', 'company_size', 'Headcount']

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        print(f"📂 Found columns: {', '.join(headers)}")

        # Find the right column names
        website_col = next((c for c in website_columns if c in headers), None)
        name_col = next((c for c in name_columns if c in headers), None)
        industry_col = next((c for c in industry_columns if c in headers), None)
        size_col = next((c for c in size_columns if c in headers), None)

        if not website_col:
            print(f"\n❌ Error: Could not find website column. Available columns: {headers}")
            print("   Please ensure your export includes company websites.")
            return

        print(f"\n✅ Using columns:")
        print(f"   Website: {website_col}")
        print(f"   Name: {name_col}")
        print(f"   Industry: {industry_col}")
        print(f"   Size: {size_col}")

        for row in reader:
            website = clean_url(row.get(website_col, ''))

            # Skip if no website or duplicate
            if not website or website in seen_domains:
                continue

            seen_domains.add(website)

            companies.append({
                'company_name': row.get(name_col, '') if name_col else '',
                'website': website,
                'industry': row.get(industry_col, '') if industry_col else 'Insurance',
                'company_size': row.get(size_col, '') if size_col else '',
                'linkedin_url': row.get('LinkedIn URL', row.get('Company LinkedIn URL', ''))
            })

    # Write cleaned output
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['company_name', 'website', 'industry', 'company_size', 'linkedin_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)

    print(f"\n📊 Results:")
    print(f"   Total rows in export: {len(seen_domains) + (len(companies) - len(seen_domains))}")
    print(f"   Companies with websites: {len(companies)}")
    print(f"   Duplicates removed: {len(seen_domains) - len(companies) if len(seen_domains) > len(companies) else 0}")
    print(f"\n✅ Saved to: {output_file}")
    print(f"\n🎯 Next step:")
    print(f"   python3 lead_finder.py --input {output_file} --output qualified_leads.csv --workers 10")


def main():
    parser = argparse.ArgumentParser(description='Prepare LinkedIn Sales Navigator export for lead checking.')
    parser.add_argument('--input', '-i', required=True, help='Input CSV from Sales Navigator')
    parser.add_argument('--output', '-o', default='companies_cleaned.csv', help='Output CSV file')

    args = parser.parse_args()

    print("\n" + "="*50)
    print("📋 LINKEDIN EXPORT PROCESSOR")
    print("="*50)

    process_linkedin_export(args.input, args.output)


if __name__ == '__main__':
    main()
