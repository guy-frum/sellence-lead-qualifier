#!/usr/bin/env python3
"""
Sellence Lead Qualifier - Web App
Upload a CSV of companies and check which ones collect phone numbers.
"""

from flask import Flask, render_template, request, jsonify, send_file
import csv
import io
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import json

app = Flask(__name__)

# Configuration
TIMEOUT = 15
MAX_WORKERS = 10
PHONE_KEYWORDS = ['phone', 'mobile', 'cell', 'tel', 'contact']

# Sellence value propositions by industry
SELLENCE_VALUE_PROPS = {
    'insurance': [
        'Increase quote completion rates by calling leads while they\'re still on the website',
        'Reduce lead response time from hours to seconds',
        'Convert more website visitors into policy holders with instant callbacks',
        'Outperform competitors who rely on slow form submissions'
    ],
    'pet_insurance': [
        'Connect with pet owners the moment they\'re comparing plans',
        'Increase quote-to-policy conversion with instant phone engagement',
        'Build trust with pet parents through immediate personal contact'
    ],
    'health_insurance': [
        'Guide prospects through complex plan options via instant callback',
        'Capture leads during open enrollment with real-time engagement',
        'Reduce drop-off rates on quote forms with immediate phone follow-up'
    ],
    'life_insurance': [
        'Build trust and rapport through immediate personal connection',
        'Answer complex coverage questions in real-time',
        'Convert hesitant prospects with timely phone engagement'
    ],
    'auto_home': [
        'Capture comparison shoppers before they leave for competitors',
        'Increase bind rates with instant quote assistance',
        'Reduce shopping abandonment with immediate callback'
    ],
    'insurtech': [
        'Differentiate from traditional insurers with instant engagement',
        'Combine digital efficiency with personal touch',
        'Increase conversion rates on your modern platform'
    ],
    'comparison': [
        'Engage high-intent shoppers at peak interest moment',
        'Convert comparison traffic into qualified leads',
        'Stand out by offering instant human connection'
    ],
    'fintech': [
        'Reduce application abandonment with instant support',
        'Build trust through immediate personal contact',
        'Convert website visitors at the moment of highest intent'
    ],
    'finance': [
        'Capture leads while they\'re actively researching',
        'Provide instant answers to complex financial questions',
        'Build trust with immediate callback'
    ],
    'education': [
        'Engage prospective students at their moment of interest',
        'Answer enrollment questions instantly',
        'Increase application completion rates'
    ],
    'default': [
        'Convert more website visitors into customers with instant callbacks',
        'Reduce lead response time from hours to seconds',
        'Engage prospects at their moment of highest intent',
        'Outperform competitors who rely on slow follow-up'
    ]
}

def get_sellence_reasons(industry, category, description=''):
    """Generate reasons why Sellence would be valuable for this company."""
    text = f"{industry} {category} {description}".lower()

    # Try to match specific industry
    for key in SELLENCE_VALUE_PROPS:
        if key in text:
            return SELLENCE_VALUE_PROPS[key][:3]

    return SELLENCE_VALUE_PROPS['default'][:3]

def normalize_url(url):
    """Normalize URL to include scheme."""
    if not url:
        return None
    url = url.strip().lower()
    url = re.sub(r'^(https?://)?(www\.)?', '', url)
    url = url.rstrip('/')
    if url:
        return f"https://www.{url}"
    return None

def extract_meta_description(soup):
    """Extract meta description from page."""
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        return meta.get('content')[:300]

    # Try og:description
    og_meta = soup.find('meta', attrs={'property': 'og:description'})
    if og_meta and og_meta.get('content'):
        return og_meta.get('content')[:300]

    return ''

def check_for_phone_field(html_content, url):
    """Check if HTML contains phone number input fields."""
    soup = BeautifulSoup(html_content, 'html.parser')
    phone_fields = []

    # Check input type="tel"
    tel_inputs = soup.find_all('input', attrs={'type': 'tel'})
    for inp in tel_inputs:
        phone_fields.append({
            'type': 'input[type=tel]',
            'name': inp.get('name', ''),
            'id': inp.get('id', ''),
            'placeholder': inp.get('placeholder', '')
        })

    # Check inputs with phone-related names/ids/placeholders
    all_inputs = soup.find_all('input')
    for inp in all_inputs:
        name = (inp.get('name', '') or '').lower()
        id_attr = (inp.get('id', '') or '').lower()
        placeholder = (inp.get('placeholder', '') or '').lower()

        for keyword in PHONE_KEYWORDS:
            if keyword in name or keyword in id_attr or keyword in placeholder:
                field_info = {
                    'type': 'input[name/id/placeholder match]',
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                    'placeholder': inp.get('placeholder', ''),
                    'matched_on': keyword
                }
                if field_info not in phone_fields:
                    phone_fields.append(field_info)
                break

    return phone_fields, soup

def check_website(company_data):
    """Check a single website for phone fields."""
    company_name = company_data.get('company_name', '')
    website = company_data.get('website', '')

    result = {
        **company_data,  # Keep all original fields
        'has_phone_field': False,
        'phone_field_details': [],
        'status': 'pending',
        'error': None,
        'scraped_description': '',
        'sellence_reasons': []
    }

    url = normalize_url(website)
    if not url:
        result['status'] = 'error'
        result['error'] = 'Invalid URL'
        return result

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        response.raise_for_status()

        phone_fields, soup = check_for_phone_field(response.text, url)

        # Extract meta description if we don't have one
        if not result.get('description'):
            result['scraped_description'] = extract_meta_description(soup)

        # Also check common subpages if no phone field found on homepage
        if not phone_fields:
            subpages = ['/contact', '/get-quote', '/quote', '/get-started', '/signup', '/sign-up']
            for subpage in subpages[:3]:
                try:
                    subpage_url = urljoin(url, subpage)
                    sub_response = requests.get(subpage_url, headers=headers, timeout=10, allow_redirects=True)
                    if sub_response.status_code == 200:
                        sub_fields, _ = check_for_phone_field(sub_response.text, subpage_url)
                        if sub_fields:
                            phone_fields = sub_fields
                            break
                except:
                    continue

        result['has_phone_field'] = len(phone_fields) > 0
        result['phone_field_details'] = phone_fields
        result['status'] = 'success'

        # Generate Sellence reasons
        industry = result.get('industry', result.get('Industry', ''))
        category = result.get('category', result.get('Category', ''))
        description = result.get('description', result.get('scraped_description', ''))
        result['sellence_reasons'] = get_sellence_reasons(industry, category, description)

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

def process_csv(file_content):
    """Process uploaded CSV and check all websites."""
    # Parse CSV
    try:
        decoded = file_content.decode('utf-8-sig')
    except:
        decoded = file_content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)

    if not rows:
        return {'error': 'CSV file is empty'}

    # Find relevant columns
    headers = reader.fieldnames

    # Column mapping for common Apollo/LinkedIn export fields
    column_mapping = {
        'company_name': ['company_name', 'Company', 'Company Name', 'name', 'Name', 'Organization Name', 'Account Name'],
        'website': ['website', 'Website', 'Company Website', 'url', 'URL', 'domain', 'Domain', 'Website URL'],
        'industry': ['industry', 'Industry', 'Category', 'category', 'Type', 'Sector'],
        'employees': ['employees', 'Employees', '# Employees', 'Employee Count', 'Number of Employees', 'Company Size', 'Size'],
        'revenue': ['revenue', 'Revenue', 'Annual Revenue', 'Company Revenue'],
        'description': ['description', 'Description', 'Company Description', 'Short Description', 'About'],
        'location': ['location', 'Location', 'City', 'Country', 'Headquarters'],
        'linkedin': ['linkedin', 'LinkedIn', 'LinkedIn URL', 'Company LinkedIn URL'],
        'founded': ['founded', 'Founded', 'Year Founded', 'Founded Year']
    }

    # Find which columns exist
    found_columns = {}
    for key, possible_names in column_mapping.items():
        for name in possible_names:
            if name in headers:
                found_columns[key] = name
                break

    if 'company_name' not in found_columns or 'website' not in found_columns:
        return {'error': f'Could not find required columns. Found: {headers}. Need company name and website columns.'}

    # Prepare companies to check with all their data
    companies = []
    for row in rows:
        company_data = {
            'company_name': row.get(found_columns.get('company_name', ''), '').strip(),
            'website': row.get(found_columns.get('website', ''), '').strip(),
        }

        # Add all other mapped fields
        for key, col_name in found_columns.items():
            if key not in ['company_name', 'website']:
                company_data[key] = row.get(col_name, '').strip()

        # Also preserve any other columns from the original CSV
        for col in headers:
            if col not in [found_columns.get(k) for k in found_columns]:
                company_data[col] = row.get(col, '').strip()

        if company_data['company_name'] and company_data['website']:
            companies.append(company_data)

    if not companies:
        return {'error': 'No valid companies found in CSV'}

    # Check websites in parallel
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_website, company): company for company in companies}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # Sort by company name
    results.sort(key=lambda x: x['company_name'])

    # Calculate stats
    qualified = [r for r in results if r['has_phone_field']]
    errors = [r for r in results if r['status'] == 'error']

    return {
        'results': results,
        'columns': list(found_columns.keys()) + ['scraped_description', 'sellence_reasons'],
        'stats': {
            'total': len(results),
            'qualified': len(qualified),
            'not_qualified': len(results) - len(qualified) - len(errors),
            'errors': len(errors),
            'qualification_rate': round(len(qualified) / len(results) * 100, 1) if results else 0
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check_companies():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400

    content = file.read()
    results = process_csv(content)

    return jsonify(results)

@app.route('/download', methods=['POST'])
def download_results():
    data = request.json
    results = data.get('results', [])
    filter_type = data.get('filter', 'qualified')

    if filter_type == 'qualified':
        filtered = [r for r in results if r.get('has_phone_field')]
    elif filter_type == 'not_qualified':
        filtered = [r for r in results if not r.get('has_phone_field') and r.get('status') != 'error']
    else:
        filtered = results

    # Create CSV with all fields
    output = io.StringIO()
    if filtered:
        # Define column order
        priority_fields = ['company_name', 'website', 'industry', 'employees', 'revenue',
                          'description', 'scraped_description', 'location', 'has_phone_field',
                          'sellence_reasons', 'status']

        # Get all unique fields
        all_fields = set()
        for r in filtered:
            all_fields.update(r.keys())

        # Order fields: priority first, then alphabetical
        fieldnames = [f for f in priority_fields if f in all_fields]
        fieldnames += sorted([f for f in all_fields if f not in priority_fields and f not in ['phone_field_details', 'error']])

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for r in filtered:
            row = {**r}
            # Convert sellence_reasons list to string
            if 'sellence_reasons' in row and isinstance(row['sellence_reasons'], list):
                row['sellence_reasons'] = ' | '.join(row['sellence_reasons'])
            writer.writerow(row)

    # Create temp file
    temp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    temp.write(output.getvalue())
    temp.close()

    return send_file(
        temp.name,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{filter_type}_leads.csv'
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*50)
    print("  SELLENCE LEAD QUALIFIER")
    print(f"  Open http://localhost:{port} in your browser")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
