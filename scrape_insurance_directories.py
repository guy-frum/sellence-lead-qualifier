#!/usr/bin/env python3
"""
Scrape insurance companies from public directories and sources.
No LinkedIn required!
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from urllib.parse import urljoin, urlparse
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def scrape_crunchbase_insurtech():
    """
    Get insurtech companies from Crunchbase's public listings.
    Note: Limited without API access.
    """
    print("   Scraping Crunchbase insurtech list...")
    # Crunchbase blocks scraping, so we use a curated list instead
    return []

def get_curated_pet_insurance():
    """Curated list of pet insurance companies."""
    return [
        {'company_name': 'Spot Pet Insurance', 'website': 'spotpetins.com', 'category': 'pet_insurance'},
        {'company_name': 'Embrace Pet Insurance', 'website': 'embracepetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Healthy Paws', 'website': 'healthypawspetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Trupanion', 'website': 'trupanion.com', 'category': 'pet_insurance'},
        {'company_name': 'Fetch Pet Insurance', 'website': 'fetchpet.com', 'category': 'pet_insurance'},
        {'company_name': 'Lemonade Pet', 'website': 'lemonade.com/pet', 'category': 'pet_insurance'},
        {'company_name': 'ASPCA Pet Insurance', 'website': 'aspcapetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Nationwide Pet', 'website': 'petinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Pets Best', 'website': 'petsbest.com', 'category': 'pet_insurance'},
        {'company_name': 'Figo Pet Insurance', 'website': 'figopetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Pumpkin Pet Insurance', 'website': 'pumpkin.care', 'category': 'pet_insurance'},
        {'company_name': 'Pawp', 'website': 'pawp.com', 'category': 'pet_insurance'},
        {'company_name': 'Wagmo', 'website': 'wagmo.io', 'category': 'pet_insurance'},
        {'company_name': 'Odie Pet Insurance', 'website': 'odiepetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Bivvy Pet Insurance', 'website': 'bivvy.com', 'category': 'pet_insurance'},
        {'company_name': 'Paw Protect', 'website': 'pawprotect.com', 'category': 'pet_insurance'},
        {'company_name': 'PHI Direct', 'website': 'phidirect.com', 'category': 'pet_insurance'},
        {'company_name': '24PetWatch', 'website': '24petwatch.com', 'category': 'pet_insurance'},
        {'company_name': 'AKC Pet Insurance', 'website': 'akcpetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Hartville Pet Insurance', 'website': 'hartvillepetinsurance.com', 'category': 'pet_insurance'},
        {'company_name': 'Prudent Pet', 'website': 'prudentpet.com', 'category': 'pet_insurance'},
        {'company_name': 'Pet Assure', 'website': 'petassure.com', 'category': 'pet_insurance'},
        {'company_name': 'Eusoh', 'website': 'eusoh.com', 'category': 'pet_insurance'},
        {'company_name': 'ManyPets', 'website': 'manypets.com', 'category': 'pet_insurance'},
        {'company_name': 'Petsure', 'website': 'petsure.com', 'category': 'pet_insurance'},
    ]

def get_curated_life_insurance():
    """Curated list of D2C life insurance companies."""
    return [
        {'company_name': 'Ethos Life', 'website': 'ethos.com', 'category': 'life_insurance'},
        {'company_name': 'Ladder', 'website': 'ladderlife.com', 'category': 'life_insurance'},
        {'company_name': 'Bestow', 'website': 'bestow.com', 'category': 'life_insurance'},
        {'company_name': 'Haven Life', 'website': 'havenlife.com', 'category': 'life_insurance'},
        {'company_name': 'Fabric', 'website': 'meetfabric.com', 'category': 'life_insurance'},
        {'company_name': 'Policygenius', 'website': 'policygenius.com', 'category': 'life_insurance'},
        {'company_name': 'Quotacy', 'website': 'quotacy.com', 'category': 'life_insurance'},
        {'company_name': 'Sproutt', 'website': 'sproutt.com', 'category': 'life_insurance'},
        {'company_name': 'Dayforward', 'website': 'dayforward.com', 'category': 'life_insurance'},
        {'company_name': 'YuLife', 'website': 'yulife.com', 'category': 'life_insurance'},
        {'company_name': 'Lemonade Life', 'website': 'lemonade.com/life', 'category': 'life_insurance'},
        {'company_name': 'Amplify Life', 'website': 'amplifylife.com', 'category': 'life_insurance'},
        {'company_name': 'Zinnia', 'website': 'zinnia.com', 'category': 'life_insurance'},
        {'company_name': 'Matic Insurance', 'website': 'matic.com', 'category': 'life_insurance'},
        {'company_name': 'Wysh Life', 'website': 'wyshlife.com', 'category': 'life_insurance'},
    ]

def get_curated_auto_home_insurance():
    """Curated list of D2C auto/home insurance companies."""
    return [
        {'company_name': 'Lemonade', 'website': 'lemonade.com', 'category': 'auto_home'},
        {'company_name': 'Root Insurance', 'website': 'root.com', 'category': 'auto_home'},
        {'company_name': 'Hippo Insurance', 'website': 'hippo.com', 'category': 'auto_home'},
        {'company_name': 'Kin Insurance', 'website': 'kin.com', 'category': 'auto_home'},
        {'company_name': 'Branch Insurance', 'website': 'ourbranch.com', 'category': 'auto_home'},
        {'company_name': 'Jerry', 'website': 'getjerry.com', 'category': 'auto_home'},
        {'company_name': 'The Zebra', 'website': 'thezebra.com', 'category': 'auto_home'},
        {'company_name': 'Insurify', 'website': 'insurify.com', 'category': 'auto_home'},
        {'company_name': 'Gabi', 'website': 'gabi.com', 'category': 'auto_home'},
        {'company_name': 'Clearcover', 'website': 'clearcover.com', 'category': 'auto_home'},
        {'company_name': 'Metromile', 'website': 'metromile.com', 'category': 'auto_home'},
        {'company_name': 'Mile Auto', 'website': 'mileauto.com', 'category': 'auto_home'},
        {'company_name': 'Openly', 'website': 'openly.com', 'category': 'auto_home'},
        {'company_name': 'Swyfft', 'website': 'swyfft.com', 'category': 'auto_home'},
        {'company_name': 'Toggle', 'website': 'toggle.com', 'category': 'auto_home'},
        {'company_name': 'Sure Insurance', 'website': 'sureapp.com', 'category': 'auto_home'},
        {'company_name': 'Bamboo Insurance', 'website': 'bambooinsurance.com', 'category': 'auto_home'},
        {'company_name': 'Neptune Flood', 'website': 'neptuneflood.com', 'category': 'auto_home'},
        {'company_name': 'Slide Insurance', 'website': 'slideinsurance.com', 'category': 'auto_home'},
        {'company_name': 'Delos Insurance', 'website': 'delosinsurance.com', 'category': 'auto_home'},
        {'company_name': 'Rhino', 'website': 'sayrhino.com', 'category': 'auto_home'},
        {'company_name': 'Jetty', 'website': 'jetty.com', 'category': 'auto_home'},
        {'company_name': 'Goodcover', 'website': 'goodcover.com', 'category': 'auto_home'},
        {'company_name': 'Kangaroo', 'website': 'heykangaroo.com', 'category': 'auto_home'},
    ]

def get_curated_health_insurance():
    """Curated list of D2C health insurance companies."""
    return [
        {'company_name': 'Oscar Health', 'website': 'hioscar.com', 'category': 'health_insurance'},
        {'company_name': 'Clover Health', 'website': 'cloverhealth.com', 'category': 'health_insurance'},
        {'company_name': 'Bright Health', 'website': 'brighthealthcare.com', 'category': 'health_insurance'},
        {'company_name': 'Collective Health', 'website': 'collectivehealth.com', 'category': 'health_insurance'},
        {'company_name': 'Sidecar Health', 'website': 'sidecarhealth.com', 'category': 'health_insurance'},
        {'company_name': 'Bind Benefits', 'website': 'yourbind.com', 'category': 'health_insurance'},
        {'company_name': 'Gravie', 'website': 'gravie.com', 'category': 'health_insurance'},
        {'company_name': 'Stride Health', 'website': 'stridehealth.com', 'category': 'health_insurance'},
        {'company_name': 'Healthmarkets', 'website': 'healthmarkets.com', 'category': 'health_insurance'},
        {'company_name': 'eHealth', 'website': 'ehealthinsurance.com', 'category': 'health_insurance'},
        {'company_name': 'GoHealth', 'website': 'gohealth.com', 'category': 'health_insurance'},
        {'company_name': 'SelectQuote', 'website': 'selectquote.com', 'category': 'health_insurance'},
        {'company_name': 'Healthsherpa', 'website': 'healthsherpa.com', 'category': 'health_insurance'},
        {'company_name': 'Decent', 'website': 'decent.com', 'category': 'health_insurance'},
        {'company_name': 'Friday Health', 'website': 'fridayhealthplans.com', 'category': 'health_insurance'},
        {'company_name': 'Alignment Healthcare', 'website': 'alignmenthealthcare.com', 'category': 'health_insurance'},
        {'company_name': 'Devoted Health', 'website': 'devoted.com', 'category': 'health_insurance'},
        {'company_name': 'Agilon Health', 'website': 'agilonhealth.com', 'category': 'health_insurance'},
    ]

def get_curated_insurance_comparison():
    """Curated list of insurance comparison/marketplace sites."""
    return [
        {'company_name': 'Policygenius', 'website': 'policygenius.com', 'category': 'comparison'},
        {'company_name': 'The Zebra', 'website': 'thezebra.com', 'category': 'comparison'},
        {'company_name': 'Insurify', 'website': 'insurify.com', 'category': 'comparison'},
        {'company_name': 'Gabi', 'website': 'gabi.com', 'category': 'comparison'},
        {'company_name': 'Jerry', 'website': 'getjerry.com', 'category': 'comparison'},
        {'company_name': 'Coverhound', 'website': 'coverhound.com', 'category': 'comparison'},
        {'company_name': 'Insureon', 'website': 'insureon.com', 'category': 'comparison'},
        {'company_name': 'Embroker', 'website': 'embroker.com', 'category': 'comparison'},
        {'company_name': 'Savvy', 'website': 'savvy.insure', 'category': 'comparison'},
        {'company_name': 'Insuranks', 'website': 'insuranks.com', 'category': 'comparison'},
        {'company_name': 'QuoteWizard', 'website': 'quotewizard.com', 'category': 'comparison'},
        {'company_name': 'ValuePenguin', 'website': 'valuepenguin.com', 'category': 'comparison'},
        {'company_name': 'NerdWallet Insurance', 'website': 'nerdwallet.com/insurance', 'category': 'comparison'},
        {'company_name': 'Bankrate Insurance', 'website': 'bankrate.com/insurance', 'category': 'comparison'},
        {'company_name': 'Insurance.com', 'website': 'insurance.com', 'category': 'comparison'},
        {'company_name': 'Insure.com', 'website': 'insure.com', 'category': 'comparison'},
        {'company_name': 'NetQuote', 'website': 'netquote.com', 'category': 'comparison'},
        {'company_name': 'SmartFinancial', 'website': 'smartfinancial.com', 'category': 'comparison'},
        {'company_name': 'EverQuote', 'website': 'everquote.com', 'category': 'comparison'},
        {'company_name': 'MediaAlpha', 'website': 'mediaalpha.com', 'category': 'comparison'},
    ]

def get_curated_insurtech_startups():
    """Curated list of insurtech startups (various categories)."""
    return [
        {'company_name': 'Wefox', 'website': 'wefox.com', 'category': 'insurtech'},
        {'company_name': 'Alan', 'website': 'alan.com', 'category': 'insurtech'},
        {'company_name': 'Next Insurance', 'website': 'nextinsurance.com', 'category': 'insurtech'},
        {'company_name': 'Coalition', 'website': 'coalitioninc.com', 'category': 'insurtech'},
        {'company_name': 'At-Bay', 'website': 'at-bay.com', 'category': 'insurtech'},
        {'company_name': 'Corvus Insurance', 'website': 'corvusinsurance.com', 'category': 'insurtech'},
        {'company_name': 'Pie Insurance', 'website': 'pieinsurance.com', 'category': 'insurtech'},
        {'company_name': 'Vouch', 'website': 'vouch.us', 'category': 'insurtech'},
        {'company_name': 'Newfront Insurance', 'website': 'newfront.com', 'category': 'insurtech'},
        {'company_name': 'Cowbell Cyber', 'website': 'cowbell.insure', 'category': 'insurtech'},
        {'company_name': 'Buckle', 'website': 'buckleup.com', 'category': 'insurtech'},
        {'company_name': 'Cape Analytics', 'website': 'capeanalytics.com', 'category': 'insurtech'},
        {'company_name': 'Snapsheet', 'website': 'snapsheet.me', 'category': 'insurtech'},
        {'company_name': 'Tractable', 'website': 'tractable.ai', 'category': 'insurtech'},
        {'company_name': 'Shift Technology', 'website': 'shift-technology.com', 'category': 'insurtech'},
        {'company_name': 'Federato', 'website': 'federato.ai', 'category': 'insurtech'},
        {'company_name': 'Highwing', 'website': 'highwing.io', 'category': 'insurtech'},
        {'company_name': 'Relativity6', 'website': 'relativity6.com', 'category': 'insurtech'},
        {'company_name': 'Socotra', 'website': 'socotra.com', 'category': 'insurtech'},
        {'company_name': 'EIS Group', 'website': 'eisgroup.com', 'category': 'insurtech'},
    ]

def search_google_for_insurance_companies(query, num_results=50):
    """
    Search Google for insurance companies.
    Note: May be rate limited.
    """
    # Google blocks automated searches, so this is just a placeholder
    # In production, you'd use Google Custom Search API or SerpAPI
    print(f"   Google search for '{query}' - requires API key for automation")
    return []

def scrape_product_hunt_insurance():
    """Get insurance products from ProductHunt."""
    print("   Checking ProductHunt for insurtech products...")
    # ProductHunt has API but requires auth
    return []

def compile_all_companies():
    """Compile companies from all sources."""
    all_companies = []

    print("\n📂 Gathering insurance companies from curated lists...")

    sources = [
        ('Pet Insurance', get_curated_pet_insurance),
        ('Life Insurance', get_curated_life_insurance),
        ('Auto/Home Insurance', get_curated_auto_home_insurance),
        ('Health Insurance', get_curated_health_insurance),
        ('Insurance Comparison', get_curated_insurance_comparison),
        ('Insurtech Startups', get_curated_insurtech_startups),
    ]

    for name, func in sources:
        companies = func()
        all_companies.extend(companies)
        print(f"   ✅ {name}: {len(companies)} companies")

    # Remove duplicates by website
    seen = set()
    unique_companies = []
    for company in all_companies:
        domain = company['website'].lower().replace('www.', '').split('/')[0]
        if domain not in seen:
            seen.add(domain)
            unique_companies.append(company)

    print(f"\n   Total unique companies: {len(unique_companies)}")
    return unique_companies

def export_to_csv(companies, output_file):
    """Export companies to CSV."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['company_name', 'website', 'category']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)

    print(f"\n✅ Exported {len(companies)} companies to {output_file}")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Scrape insurance companies from public directories.',
        epilog="""
Examples:
  python3 scrape_insurance_directories.py --output insurance_companies.csv
  python3 scrape_insurance_directories.py --category pet_insurance
        """
    )
    parser.add_argument('--output', '-o', default='scraped_insurance.csv', help='Output CSV file')
    parser.add_argument('--category', '-c', help='Filter by category (pet_insurance, life_insurance, auto_home, health_insurance, comparison, insurtech)')

    args = parser.parse_args()

    print("\n" + "="*50)
    print("🔍 INSURANCE COMPANY SCRAPER")
    print("   No LinkedIn required!")
    print("="*50)

    companies = compile_all_companies()

    if args.category:
        companies = [c for c in companies if c.get('category') == args.category]
        print(f"\n   Filtered to category '{args.category}': {len(companies)} companies")

    export_to_csv(companies, args.output)

    print(f"\n🎯 Next step:")
    print(f"   python3 lead_finder.py --input {args.output} --output qualified_leads.csv")

if __name__ == '__main__':
    main()
