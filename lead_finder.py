#!/usr/bin/env python3
"""
Sellence Lead Finder
Finds companies that collect phone numbers on their websites.
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import argparse
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Phone field indicators
PHONE_INDICATORS = [
    'phone', 'tel', 'mobile', 'cell', 'contact_number', 'phone_number',
    'phonenumber', 'telephone', 'contact-phone', 'phone-number', 'phoneNumber'
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def check_for_phone_field(html_content, url):
    """
    Check if the HTML contains a phone number input field.
    Returns dict with details about what was found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    phone_fields_found = []

    # Check for input type="tel"
    tel_inputs = soup.find_all('input', attrs={'type': 'tel'})
    for inp in tel_inputs:
        phone_fields_found.append({
            'type': 'input[type=tel]',
            'name': inp.get('name', ''),
            'id': inp.get('id', ''),
            'placeholder': inp.get('placeholder', '')
        })

    # Check for inputs with phone-related names/ids/placeholders
    all_inputs = soup.find_all('input')
    for inp in all_inputs:
        name = (inp.get('name', '') or '').lower()
        id_attr = (inp.get('id', '') or '').lower()
        placeholder = (inp.get('placeholder', '') or '').lower()
        label_text = ''

        # Check for associated label
        if inp.get('id'):
            label = soup.find('label', attrs={'for': inp.get('id')})
            if label:
                label_text = label.get_text().lower()

        # Check if any phone indicators match
        for indicator in PHONE_INDICATORS:
            if (indicator in name or indicator in id_attr or
                indicator in placeholder or indicator in label_text):
                # Avoid duplicates from type="tel"
                if inp.get('type') != 'tel':
                    phone_fields_found.append({
                        'type': 'input[name/id/placeholder match]',
                        'name': inp.get('name', ''),
                        'id': inp.get('id', ''),
                        'placeholder': inp.get('placeholder', ''),
                        'matched_on': indicator
                    })
                break

    # Check for forms in general
    forms = soup.find_all('form')

    return {
        'has_phone_field': len(phone_fields_found) > 0,
        'phone_fields': phone_fields_found,
        'total_forms': len(forms)
    }


def find_form_pages(base_url, html_content):
    """
    Find links to pages that likely contain forms (contact, quote, demo, etc.)
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    form_keywords = [
        'contact', 'quote', 'get-quote', 'get-a-quote', 'request', 'demo',
        'signup', 'sign-up', 'register', 'get-started', 'trial', 'pricing',
        'apply', 'enroll', 'inquiry', 'enquiry', 'lead', 'form'
    ]

    form_pages = []
    links = soup.find_all('a', href=True)

    for link in links:
        href = link.get('href', '').lower()
        text = link.get_text().lower()

        for keyword in form_keywords:
            if keyword in href or keyword in text:
                full_url = urljoin(base_url, link.get('href'))
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    if full_url not in form_pages:
                        form_pages.append(full_url)
                break

    return form_pages[:5]  # Limit to 5 pages to avoid overloading


def check_website(url, check_subpages=True):
    """
    Check a website for phone number collection.
    """
    if not url.startswith('http'):
        url = 'https://' + url

    result = {
        'url': url,
        'status': 'unknown',
        'has_phone_field': False,
        'phone_fields': [],
        'pages_checked': [],
        'error': None
    }

    try:
        # Check main page
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        response.raise_for_status()

        result['final_url'] = response.url
        main_check = check_for_phone_field(response.text, url)
        result['pages_checked'].append({'url': url, 'result': main_check})

        if main_check['has_phone_field']:
            result['has_phone_field'] = True
            result['phone_fields'].extend(main_check['phone_fields'])

        # Check subpages if enabled and no phone field found yet
        if check_subpages and not result['has_phone_field']:
            form_pages = find_form_pages(url, response.text)

            for page_url in form_pages:
                try:
                    time.sleep(0.5)  # Be respectful
                    page_response = requests.get(page_url, headers=HEADERS, timeout=10)
                    page_check = check_for_phone_field(page_response.text, page_url)
                    result['pages_checked'].append({'url': page_url, 'result': page_check})

                    if page_check['has_phone_field']:
                        result['has_phone_field'] = True
                        result['phone_fields'].extend(page_check['phone_fields'])
                        break  # Found what we need
                except Exception as e:
                    pass  # Ignore subpage errors

        result['status'] = 'success'

    except requests.exceptions.Timeout:
        result['status'] = 'error'
        result['error'] = 'Timeout'
    except requests.exceptions.RequestException as e:
        result['status'] = 'error'
        result['error'] = str(e)[:100]
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)[:100]

    return result


def process_csv(input_file, output_file, url_column='website', check_subpages=True, max_workers=5):
    """
    Process a CSV file of companies and check each website.
    """
    results = []
    qualified_leads = []

    # Read input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"\n📂 Loaded {len(rows)} companies from {input_file}")
    print(f"🔍 Checking websites for phone number fields...\n")

    # Process websites
    total = len(rows)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_row = {}

        for row in rows:
            url = row.get(url_column, '').strip()
            if url:
                future = executor.submit(check_website, url, check_subpages)
                future_to_row[future] = row

        for future in as_completed(future_to_row):
            row = future_to_row[future]
            completed += 1

            try:
                result = future.result()
                row['_has_phone_field'] = result['has_phone_field']
                row['_phone_field_details'] = json.dumps(result['phone_fields']) if result['phone_fields'] else ''
                row['_check_status'] = result['status']
                row['_error'] = result.get('error', '')

                status_icon = '✅' if result['has_phone_field'] else '❌'
                print(f"  [{completed}/{total}] {status_icon} {row.get(url_column, 'Unknown')[:50]}")

                if result['has_phone_field']:
                    qualified_leads.append(row)

            except Exception as e:
                row['_has_phone_field'] = False
                row['_check_status'] = 'error'
                row['_error'] = str(e)
                print(f"  [{completed}/{total}] ⚠️ {row.get(url_column, 'Unknown')[:50]} - Error")

            results.append(row)

    # Write results
    output_fieldnames = fieldnames + ['_has_phone_field', '_phone_field_details', '_check_status', '_error']

    # Write all results
    all_results_file = output_file.replace('.csv', '_all.csv')
    with open(all_results_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Write qualified leads only
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(qualified_leads)

    print(f"\n{'='*50}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*50}")
    print(f"   Total companies checked: {len(results)}")
    print(f"   ✅ With phone fields:    {len(qualified_leads)}")
    print(f"   ❌ Without phone fields: {len(results) - len(qualified_leads)}")
    print(f"   Qualification rate:      {len(qualified_leads)/len(results)*100:.1f}%")
    print(f"\n📁 Output files:")
    print(f"   Qualified leads: {output_file}")
    print(f"   All results:     {all_results_file}")

    return qualified_leads


def check_single_website(url):
    """Check a single website and print results."""
    print(f"\n🔍 Checking: {url}")
    print("-" * 50)

    result = check_website(url, check_subpages=True)

    if result['status'] == 'error':
        print(f"❌ Error: {result['error']}")
        return

    if result['has_phone_field']:
        print(f"✅ QUALIFIED - Phone number field found!")
        print(f"\nPhone fields detected:")
        for field in result['phone_fields']:
            print(f"   - Type: {field['type']}")
            if field.get('name'):
                print(f"     Name: {field['name']}")
            if field.get('placeholder'):
                print(f"     Placeholder: {field['placeholder']}")
    else:
        print(f"❌ NOT QUALIFIED - No phone number field found")
        print(f"   Pages checked: {len(result['pages_checked'])}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Find companies that collect phone numbers on their websites.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a single website
  python lead_finder.py --url https://example.com

  # Process a CSV file
  python lead_finder.py --input companies.csv --output qualified_leads.csv

  # Process CSV with custom website column name
  python lead_finder.py --input companies.csv --output leads.csv --url-column "Website URL"
        """
    )

    parser.add_argument('--url', type=str, help='Single website URL to check')
    parser.add_argument('--input', type=str, help='Input CSV file with company websites')
    parser.add_argument('--output', type=str, default='qualified_leads.csv', help='Output CSV file for qualified leads')
    parser.add_argument('--url-column', type=str, default='website', help='Name of the column containing website URLs')
    parser.add_argument('--no-subpages', action='store_true', help='Only check homepage, not subpages')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')

    args = parser.parse_args()

    print("\n" + "="*50)
    print("🎯 SELLENCE LEAD FINDER")
    print("   Find companies that collect phone numbers")
    print("="*50)

    if args.url:
        check_single_website(args.url)
    elif args.input:
        process_csv(
            args.input,
            args.output,
            url_column=args.url_column,
            check_subpages=not args.no_subpages,
            max_workers=args.workers
        )
    else:
        parser.print_help()
        print("\n💡 Quick start:")
        print("   1. Create a CSV with a 'website' column")
        print("   2. Run: python lead_finder.py --input your_companies.csv")


if __name__ == '__main__':
    main()
