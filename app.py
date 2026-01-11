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

    return phone_fields

def check_website(company_name, website, category=''):
    """Check a single website for phone fields."""
    result = {
        'company_name': company_name,
        'website': website,
        'category': category,
        'has_phone_field': False,
        'phone_field_details': [],
        'status': 'pending',
        'error': None
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

        phone_fields = check_for_phone_field(response.text, url)

        # Also check common subpages if no phone field found on homepage
        if not phone_fields:
            subpages = ['/contact', '/get-quote', '/quote', '/get-started', '/signup', '/sign-up']
            for subpage in subpages[:3]:  # Limit to 3 subpages
                try:
                    subpage_url = urljoin(url, subpage)
                    sub_response = requests.get(subpage_url, headers=headers, timeout=10, allow_redirects=True)
                    if sub_response.status_code == 200:
                        sub_fields = check_for_phone_field(sub_response.text, subpage_url)
                        if sub_fields:
                            phone_fields = sub_fields
                            break
                except:
                    continue

        result['has_phone_field'] = len(phone_fields) > 0
        result['phone_field_details'] = phone_fields
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

def process_csv(file_content):
    """Process uploaded CSV and check all websites."""
    # Parse CSV
    try:
        decoded = file_content.decode('utf-8-sig')
    except:
        decoded = file_content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)

    # Find relevant columns
    headers = reader.fieldnames

    # Company name columns
    name_cols = ['company_name', 'Company', 'Company Name', 'name', 'Name', 'Organization Name']
    name_col = next((c for c in name_cols if c in headers), None)

    # Website columns
    website_cols = ['website', 'Website', 'Company Website', 'url', 'URL', 'domain', 'Domain']
    website_col = next((c for c in website_cols if c in headers), None)

    # Category column (optional)
    category_cols = ['category', 'Category', 'Industry', 'industry', 'Type']
    category_col = next((c for c in category_cols if c in headers), None)

    if not name_col or not website_col:
        return {'error': f'Could not find required columns. Found: {headers}. Need company name and website columns.'}

    # Prepare companies to check
    companies = []
    for row in rows:
        name = row.get(name_col, '').strip()
        website = row.get(website_col, '').strip()
        category = row.get(category_col, '').strip() if category_col else ''

        if name and website:
            companies.append((name, website, category))

    if not companies:
        return {'error': 'No valid companies found in CSV'}

    # Check websites in parallel
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(check_website, name, website, category): (name, website)
            for name, website, category in companies
        }

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
    filter_type = data.get('filter', 'qualified')  # 'qualified', 'all', 'not_qualified'

    if filter_type == 'qualified':
        filtered = [r for r in results if r['has_phone_field']]
    elif filter_type == 'not_qualified':
        filtered = [r for r in results if not r['has_phone_field']]
    else:
        filtered = results

    # Create CSV
    output = io.StringIO()
    if filtered:
        fieldnames = ['company_name', 'website', 'category', 'has_phone_field', 'status']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in filtered:
            writer.writerow({
                'company_name': r['company_name'],
                'website': r['website'],
                'category': r['category'],
                'has_phone_field': r['has_phone_field'],
                'status': r['status']
            })

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
    import os
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*50)
    print("  SELLENCE LEAD QUALIFIER")
    print(f"  Open http://localhost:{port} in your browser")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
