#!/usr/bin/env python3
"""
Find companies in target verticals from various sources.
Works with Apollo.io API or can scrape from public directories.
"""

import requests
import csv
import json
import argparse
import time
from typing import List, Dict

# Industry search terms for each vertical
VERTICALS = {
    'insurance': [
        'insurance company', 'insurtech', 'insurance carrier',
        'pet insurance', 'life insurance', 'health insurance',
        'auto insurance', 'home insurance', 'insurance platform'
    ],
    'education': [
        'coding bootcamp', 'online education', 'edtech',
        'vocational school', 'professional certification',
        'online university', 'career training', 'test prep'
    ],
    'finance': [
        'fintech', 'neobank', 'digital bank', 'lending platform',
        'trading platform', 'investment app', 'crypto exchange',
        'financial services', 'payment platform'
    ],
    'real_estate': [
        'mortgage lender', 'digital mortgage', 'home loans',
        'real estate fintech', 'heloc', 'home equity',
        'mortgage platform', 'refinance'
    ],
    'ecommerce': [
        'luxury ecommerce', 'premium retail', 'high-end online store',
        'custom products', 'furniture ecommerce', 'jewelry online'
    ]
}

# Company size filters (employee count)
SIZE_FILTERS = {
    'small': (10, 50),
    'mid': (50, 500),
    'large': (500, 5000)
}


def search_apollo(api_key: str, vertical: str, size: str = 'mid', limit: int = 100) -> List[Dict]:
    """
    Search for companies using Apollo.io API.
    Requires Apollo API key.
    """
    base_url = "https://api.apollo.io/v1/mixed_companies/search"

    keywords = VERTICALS.get(vertical, [vertical])
    size_range = SIZE_FILTERS.get(size, (50, 500))

    results = []

    for keyword in keywords:
        payload = {
            "api_key": api_key,
            "q_organization_keyword_tags": [keyword],
            "organization_num_employees_ranges": [f"{size_range[0]},{size_range[1]}"],
            "page": 1,
            "per_page": min(limit, 100)
        }

        try:
            response = requests.post(base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            for company in data.get('organizations', []):
                results.append({
                    'company_name': company.get('name', ''),
                    'website': company.get('website_url', ''),
                    'industry': company.get('industry', ''),
                    'employees': company.get('estimated_num_employees', ''),
                    'linkedin': company.get('linkedin_url', ''),
                    'description': company.get('short_description', '')[:200] if company.get('short_description') else '',
                    'source': 'apollo',
                    'vertical': vertical,
                    'search_keyword': keyword
                })

            print(f"   Found {len(data.get('organizations', []))} companies for '{keyword}'")
            time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"   Error searching '{keyword}': {e}")

        if len(results) >= limit:
            break

    return results[:limit]


def generate_sample_list(vertical: str, count: int = 20) -> List[Dict]:
    """
    Generate a sample list of companies to research manually.
    This provides example company names you can then find websites for.
    """

    sample_companies = {
        'insurance': [
            {'company_name': 'Lemonade', 'website': 'lemonade.com', 'vertical': 'insurance'},
            {'company_name': 'Root Insurance', 'website': 'root.com', 'vertical': 'insurance'},
            {'company_name': 'Hippo Insurance', 'website': 'hippo.com', 'vertical': 'insurance'},
            {'company_name': 'Ethos Life', 'website': 'ethos.com', 'vertical': 'insurance'},
            {'company_name': 'Ladder', 'website': 'ladderlife.com', 'vertical': 'insurance'},
            {'company_name': 'Bestow', 'website': 'bestow.com', 'vertical': 'insurance'},
            {'company_name': 'Policygenius', 'website': 'policygenius.com', 'vertical': 'insurance'},
            {'company_name': 'The Zebra', 'website': 'thezebra.com', 'vertical': 'insurance'},
            {'company_name': 'Insurify', 'website': 'insurify.com', 'vertical': 'insurance'},
            {'company_name': 'Jerry', 'website': 'getjerry.com', 'vertical': 'insurance'},
            {'company_name': 'Spot Pet Insurance', 'website': 'spotpetins.com', 'vertical': 'insurance'},
            {'company_name': 'Embrace Pet Insurance', 'website': 'embracepetinsurance.com', 'vertical': 'insurance'},
            {'company_name': 'Fetch Pet Insurance', 'website': 'fetchpet.com', 'vertical': 'insurance'},
            {'company_name': 'Healthy Paws', 'website': 'healthypawspetinsurance.com', 'vertical': 'insurance'},
            {'company_name': 'Trupanion', 'website': 'trupanion.com', 'vertical': 'insurance'},
            {'company_name': 'Oscar Health', 'website': 'hioscar.com', 'vertical': 'insurance'},
            {'company_name': 'Clover Health', 'website': 'cloverhealth.com', 'vertical': 'insurance'},
            {'company_name': 'Bright Health', 'website': 'brighthealthcare.com', 'vertical': 'insurance'},
            {'company_name': 'Kin Insurance', 'website': 'kin.com', 'vertical': 'insurance'},
            {'company_name': 'Branch Insurance', 'website': 'ourbranch.com', 'vertical': 'insurance'},
        ],
        'education': [
            {'company_name': 'General Assembly', 'website': 'generalassemb.ly', 'vertical': 'education'},
            {'company_name': 'Flatiron School', 'website': 'flatironschool.com', 'vertical': 'education'},
            {'company_name': 'Springboard', 'website': 'springboard.com', 'vertical': 'education'},
            {'company_name': 'Thinkful', 'website': 'thinkful.com', 'vertical': 'education'},
            {'company_name': 'Codecademy', 'website': 'codecademy.com', 'vertical': 'education'},
            {'company_name': 'Udacity', 'website': 'udacity.com', 'vertical': 'education'},
            {'company_name': 'Coursera', 'website': 'coursera.org', 'vertical': 'education'},
            {'company_name': 'edX', 'website': 'edx.org', 'vertical': 'education'},
            {'company_name': 'Skillshare', 'website': 'skillshare.com', 'vertical': 'education'},
            {'company_name': 'MasterClass', 'website': 'masterclass.com', 'vertical': 'education'},
            {'company_name': 'Lambda School', 'website': 'lambdaschool.com', 'vertical': 'education'},
            {'company_name': 'App Academy', 'website': 'appacademy.io', 'vertical': 'education'},
            {'company_name': 'Hack Reactor', 'website': 'hackreactor.com', 'vertical': 'education'},
            {'company_name': 'BrainStation', 'website': 'brainstation.io', 'vertical': 'education'},
            {'company_name': 'CareerFoundry', 'website': 'careerfoundry.com', 'vertical': 'education'},
            {'company_name': 'Kaplan', 'website': 'kaplan.com', 'vertical': 'education'},
            {'company_name': 'Princeton Review', 'website': 'princetonreview.com', 'vertical': 'education'},
            {'company_name': 'Magoosh', 'website': 'magoosh.com', 'vertical': 'education'},
            {'company_name': 'SNHU', 'website': 'snhu.edu', 'vertical': 'education'},
            {'company_name': 'Western Governors', 'website': 'wgu.edu', 'vertical': 'education'},
        ],
        'finance': [
            {'company_name': 'Robinhood', 'website': 'robinhood.com', 'vertical': 'finance'},
            {'company_name': 'Coinbase', 'website': 'coinbase.com', 'vertical': 'finance'},
            {'company_name': 'SoFi', 'website': 'sofi.com', 'vertical': 'finance'},
            {'company_name': 'Chime', 'website': 'chime.com', 'vertical': 'finance'},
            {'company_name': 'Revolut', 'website': 'revolut.com', 'vertical': 'finance'},
            {'company_name': 'Cash App', 'website': 'cash.app', 'vertical': 'finance'},
            {'company_name': 'Venmo', 'website': 'venmo.com', 'vertical': 'finance'},
            {'company_name': 'Public', 'website': 'public.com', 'vertical': 'finance'},
            {'company_name': 'Webull', 'website': 'webull.com', 'vertical': 'finance'},
            {'company_name': 'eToro', 'website': 'etoro.com', 'vertical': 'finance'},
            {'company_name': 'Acorns', 'website': 'acorns.com', 'vertical': 'finance'},
            {'company_name': 'Stash', 'website': 'stash.com', 'vertical': 'finance'},
            {'company_name': 'Betterment', 'website': 'betterment.com', 'vertical': 'finance'},
            {'company_name': 'Wealthfront', 'website': 'wealthfront.com', 'vertical': 'finance'},
            {'company_name': 'Kraken', 'website': 'kraken.com', 'vertical': 'finance'},
            {'company_name': 'Gemini', 'website': 'gemini.com', 'vertical': 'finance'},
            {'company_name': 'LendingClub', 'website': 'lendingclub.com', 'vertical': 'finance'},
            {'company_name': 'Upstart', 'website': 'upstart.com', 'vertical': 'finance'},
            {'company_name': 'Upgrade', 'website': 'upgrade.com', 'vertical': 'finance'},
            {'company_name': 'Current', 'website': 'current.com', 'vertical': 'finance'},
        ],
        'real_estate': [
            {'company_name': 'Better.com', 'website': 'better.com', 'vertical': 'real_estate'},
            {'company_name': 'Rocket Mortgage', 'website': 'rocketmortgage.com', 'vertical': 'real_estate'},
            {'company_name': 'LoanDepot', 'website': 'loandepot.com', 'vertical': 'real_estate'},
            {'company_name': 'Figure', 'website': 'figure.com', 'vertical': 'real_estate'},
            {'company_name': 'Hometap', 'website': 'hometap.com', 'vertical': 'real_estate'},
            {'company_name': 'Point', 'website': 'point.com', 'vertical': 'real_estate'},
            {'company_name': 'Guaranteed Rate', 'website': 'rate.com', 'vertical': 'real_estate'},
            {'company_name': 'Credible', 'website': 'credible.com', 'vertical': 'real_estate'},
            {'company_name': 'LendingTree', 'website': 'lendingtree.com', 'vertical': 'real_estate'},
            {'company_name': 'Bankrate', 'website': 'bankrate.com', 'vertical': 'real_estate'},
            {'company_name': 'Blend', 'website': 'blend.com', 'vertical': 'real_estate'},
            {'company_name': 'Quontic', 'website': 'quontic.com', 'vertical': 'real_estate'},
            {'company_name': 'Arrived', 'website': 'arrived.com', 'vertical': 'real_estate'},
            {'company_name': 'Divvy', 'website': 'divvyhomes.com', 'vertical': 'real_estate'},
            {'company_name': 'Aven', 'website': 'aven.com', 'vertical': 'real_estate'},
        ],
        'ecommerce': [
            {'company_name': 'Heavys', 'website': 'heavys.com', 'vertical': 'ecommerce'},
            {'company_name': 'Warby Parker', 'website': 'warbyparker.com', 'vertical': 'ecommerce'},
            {'company_name': 'Allbirds', 'website': 'allbirds.com', 'vertical': 'ecommerce'},
            {'company_name': 'Away', 'website': 'awaytravel.com', 'vertical': 'ecommerce'},
            {'company_name': 'Casper', 'website': 'casper.com', 'vertical': 'ecommerce'},
            {'company_name': 'Purple', 'website': 'purple.com', 'vertical': 'ecommerce'},
            {'company_name': 'Article', 'website': 'article.com', 'vertical': 'ecommerce'},
            {'company_name': 'Burrow', 'website': 'burrow.com', 'vertical': 'ecommerce'},
            {'company_name': 'Floyd', 'website': 'floydhome.com', 'vertical': 'ecommerce'},
            {'company_name': 'Joybird', 'website': 'joybird.com', 'vertical': 'ecommerce'},
            {'company_name': 'Interior Define', 'website': 'interiordefine.com', 'vertical': 'ecommerce'},
            {'company_name': 'Brooklinen', 'website': 'brooklinen.com', 'vertical': 'ecommerce'},
            {'company_name': 'Parachute', 'website': 'parachutehome.com', 'vertical': 'ecommerce'},
            {'company_name': 'Outer', 'website': 'liveouter.com', 'vertical': 'ecommerce'},
            {'company_name': 'Crate & Barrel', 'website': 'crateandbarrel.com', 'vertical': 'ecommerce'},
        ]
    }

    companies = sample_companies.get(vertical, [])
    return companies[:count]


def export_to_csv(companies: List[Dict], output_file: str):
    """Export companies to CSV."""
    if not companies:
        print("No companies to export.")
        return

    fieldnames = companies[0].keys()

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)

    print(f"\n✅ Exported {len(companies)} companies to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Find companies in target verticals for lead generation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate sample insurance companies list
  python find_companies.py --vertical insurance --output insurance_companies.csv

  # Use Apollo API to find companies
  python find_companies.py --vertical insurance --apollo-key YOUR_API_KEY --limit 100

  # Generate list for all verticals
  python find_companies.py --all-verticals --output all_companies.csv
        """
    )

    parser.add_argument('--vertical', type=str, choices=list(VERTICALS.keys()),
                        help='Target vertical (insurance, education, finance, real_estate, ecommerce)')
    parser.add_argument('--all-verticals', action='store_true',
                        help='Generate companies from all verticals')
    parser.add_argument('--apollo-key', type=str,
                        help='Apollo.io API key for live search')
    parser.add_argument('--limit', type=int, default=20,
                        help='Number of companies to find (default: 20)')
    parser.add_argument('--output', type=str, default='companies.csv',
                        help='Output CSV file')

    args = parser.parse_args()

    print("\n" + "="*50)
    print("🏢 COMPANY FINDER")
    print("   Find companies in your target verticals")
    print("="*50 + "\n")

    all_companies = []

    if args.all_verticals:
        verticals = list(VERTICALS.keys())
    elif args.vertical:
        verticals = [args.vertical]
    else:
        parser.print_help()
        print("\n💡 Quick start:")
        print("   python find_companies.py --vertical insurance --output insurance_leads.csv")
        return

    for vertical in verticals:
        print(f"\n📂 Finding {vertical} companies...")

        if args.apollo_key:
            companies = search_apollo(args.apollo_key, vertical, limit=args.limit)
        else:
            companies = generate_sample_list(vertical, args.limit)

        all_companies.extend(companies)
        print(f"   Found {len(companies)} companies")

    export_to_csv(all_companies, args.output)

    print(f"\n🎯 Next step: Check which companies collect phone numbers:")
    print(f"   python lead_finder.py --input {args.output} --output qualified_leads.csv")


if __name__ == '__main__':
    main()
