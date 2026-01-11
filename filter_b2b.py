#!/usr/bin/env python3
"""
Filter out B2B insurance companies from a list.
Keeps only B2C/D2C companies that are relevant for Sellence.
"""

import csv
import re
import argparse

# B2B indicators - if company name or description contains these, likely B2B
B2B_KEYWORDS = [
    # Business insurance types
    'commercial insurance', 'commercial lines', 'business insurance',
    'workers comp', 'workers compensation', 'workman comp',
    'liability insurance', 'professional liability', 'general liability',
    'e&o', 'errors and omissions', 'd&o', 'directors and officers',
    'cyber insurance', 'cyber liability',
    'employee benefits', 'group insurance', 'group health',
    'corporate insurance', 'enterprise risk',
    'property & casualty', 'p&c', 'property and casualty',
    'wholesale insurance', 'wholesale broker',
    'reinsurance', 'reinsurer',
    'captive insurance', 'risk retention',
    'surety bond', 'fidelity bond',
    'marine insurance', 'cargo insurance',
    'aviation insurance', 'aircraft insurance',
    'construction insurance', 'builder risk',
    'fleet insurance', 'commercial auto',
    'business owner policy', 'bop',
    'employer', 'workplace',

    # B2B service providers
    'insurance broker', 'insurance agency', 'insurance agent',
    'mga', 'managing general', 'program administrator',
    'tpa', 'third party administrator', 'claims administrator',
    'insurance software', 'insurance platform', 'insurance saas',
    'policy administration', 'claims management',
    'underwriting', 'actuarial',
    'insurance consulting', 'risk consulting',
    'loss control', 'risk management',

    # Other B2B indicators
    'b2b', 'enterprise', 'small business', 'smb',
    'fortune 500', 'mid-market',
    'insurance carrier services', 'carrier services',
]

# B2C indicators - if these are present, likely B2C (override B2B)
B2C_KEYWORDS = [
    'pet insurance', 'pet health',
    'life insurance', 'term life', 'whole life',
    'auto insurance', 'car insurance',
    'home insurance', 'homeowners', 'homeowner',
    'renters insurance', 'renter insurance',
    'health insurance', 'medical insurance',
    'dental insurance', 'vision insurance',
    'travel insurance', 'trip insurance',
    'medicare', 'medicaid', 'medigap',
    'individual', 'personal insurance', 'personal lines',
    'family insurance', 'family plan',
    'quote', 'get a quote', 'free quote',
    'd2c', 'direct to consumer', 'direct-to-consumer',
    'insurtech',
    'mobile app', 'insurance app',
    'compare insurance', 'comparison',
]

def is_b2b(text):
    """Check if text indicates B2B company."""
    text_lower = text.lower()

    # First check for strong B2C indicators
    for keyword in B2C_KEYWORDS:
        if keyword in text_lower:
            return False  # Likely B2C, don't filter out

    # Then check for B2B indicators
    for keyword in B2B_KEYWORDS:
        if keyword in text_lower:
            return True  # Likely B2B, filter out

    return False  # Unknown, keep it

def filter_companies(input_file, output_file):
    """Filter out B2B companies from CSV."""

    b2c_companies = []
    b2b_companies = []

    # Possible column names to check for B2B keywords
    text_columns = ['company_name', 'Company', 'Name', 'name',
                    'description', 'Description', 'Company Description',
                    'industry', 'Industry', 'Specialties', 'specialties',
                    'tagline', 'Tagline', 'headline', 'Headline']

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        # Find which text columns exist
        available_columns = [c for c in text_columns if c in headers]

        for row in reader:
            # Combine all text fields to check
            combined_text = ' '.join([
                str(row.get(col, '')) for col in available_columns
            ])

            if is_b2b(combined_text):
                b2b_companies.append(row)
            else:
                b2c_companies.append(row)

    # Write B2C companies (the ones we want)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(b2c_companies)

    # Write B2B companies to separate file for review
    b2b_file = output_file.replace('.csv', '_b2b_removed.csv')
    with open(b2b_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(b2b_companies)

    print(f"\n📊 FILTERING RESULTS")
    print(f"="*50)
    print(f"   Total companies:     {len(b2c_companies) + len(b2b_companies)}")
    print(f"   ✅ B2C (kept):       {len(b2c_companies)}")
    print(f"   ❌ B2B (removed):    {len(b2b_companies)}")
    print(f"\n📁 Output files:")
    print(f"   B2C companies: {output_file}")
    print(f"   B2B removed:   {b2b_file}")

    return b2c_companies

def main():
    parser = argparse.ArgumentParser(
        description='Filter out B2B insurance companies, keep only B2C.',
        epilog="""
Example:
  python3 filter_b2b.py --input companies.csv --output b2c_companies.csv
        """
    )
    parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    parser.add_argument('--output', '-o', default='b2c_companies.csv', help='Output CSV file')

    args = parser.parse_args()

    print("\n" + "="*50)
    print("🎯 B2B FILTER")
    print("   Removing B2B insurance companies")
    print("="*50)

    filter_companies(args.input, args.output)

if __name__ == '__main__':
    main()
