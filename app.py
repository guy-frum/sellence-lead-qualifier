#!/usr/bin/env python3
"""
Sellence Lead Qualifier - Web App
Upload a CSV of companies and check which ones collect phone numbers.
Uses Playwright for JavaScript rendering to catch dynamic forms.
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

# Try to import playwright, fall back to requests-only mode
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available, using requests-only mode")

app = Flask(__name__)

# Configuration
TIMEOUT = 20000  # 20 seconds for playwright
REQUEST_TIMEOUT = 15
MAX_WORKERS = 5  # Fewer workers since browser is heavier
PHONE_KEYWORDS = ['phone', 'mobile', 'cell', 'tel', 'telephone', 'contact', 'callback', 'call me', 'call-me']

# Extended list of pages to check
PAGES_TO_CHECK = [
    '/',
    '/contact',
    '/contact-us',
    '/get-quote',
    '/quote',
    '/get-a-quote',
    '/free-quote',
    '/get-started',
    '/start',
    '/signup',
    '/sign-up',
    '/register',
    '/demo',
    '/request-demo',
    '/book-demo',
    '/schedule',
    '/schedule-call',
    '/talk-to-us',
    '/lets-talk',
    '/request-callback',
    '/callback',
    '/apply',
    '/enroll',
    '/get-pricing',
    '/pricing',
]

# Buttons to click that might reveal forms
BUTTON_PATTERNS = [
    'get quote', 'get a quote', 'free quote', 'start quote',
    'get started', 'start now', 'begin', 'apply now',
    'contact us', 'contact sales', 'talk to us', 'speak to',
    'request callback', 'call me', 'call back', 'schedule call',
    'book demo', 'request demo', 'get demo', 'see demo',
    'sign up', 'register', 'enroll', 'join',
    'get pricing', 'see pricing', 'view pricing',
    'learn more', 'find out more',
]

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
    for key in SELLENCE_VALUE_PROPS:
        if key in text:
            return SELLENCE_VALUE_PROPS[key][:3]
    return SELLENCE_VALUE_PROPS['default'][:3]

def normalize_url(url):
    """Normalize URL to include scheme."""
    if not url:
        return None
    url = url.strip()
    # Remove protocol and www
    url = re.sub(r'^(https?://)?(www\.)?', '', url, flags=re.IGNORECASE)
    url = url.rstrip('/')
    if url:
        return f"https://{url}"
    return None

def extract_meta_description(soup):
    """Extract meta description from page."""
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        return meta.get('content')[:300]
    og_meta = soup.find('meta', attrs={'property': 'og:description'})
    if og_meta and og_meta.get('content'):
        return og_meta.get('content')[:300]
    return ''

def check_html_for_phone_fields(html_content):
    """Check HTML content for phone number input fields."""
    soup = BeautifulSoup(html_content, 'html.parser')
    phone_fields = []

    # 1. Check input type="tel"
    tel_inputs = soup.find_all('input', attrs={'type': 'tel'})
    for inp in tel_inputs:
        phone_fields.append({
            'type': 'input[type=tel]',
            'name': inp.get('name', ''),
            'id': inp.get('id', ''),
            'placeholder': inp.get('placeholder', ''),
            'detection': 'type=tel'
        })

    # 2. Check all inputs for phone-related attributes
    all_inputs = soup.find_all('input')
    for inp in all_inputs:
        input_type = (inp.get('type', '') or '').lower()
        if input_type in ['hidden', 'submit', 'button', 'checkbox', 'radio', 'file']:
            continue

        name = (inp.get('name', '') or '').lower()
        id_attr = (inp.get('id', '') or '').lower()
        placeholder = (inp.get('placeholder', '') or '').lower()
        aria_label = (inp.get('aria-label', '') or '').lower()
        class_attr = ' '.join(inp.get('class', [])).lower() if inp.get('class') else ''

        combined = f"{name} {id_attr} {placeholder} {aria_label} {class_attr}"

        for keyword in PHONE_KEYWORDS:
            if keyword in combined:
                field_info = {
                    'type': 'input[keyword match]',
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                    'placeholder': inp.get('placeholder', ''),
                    'detection': f'keyword: {keyword}'
                }
                if field_info not in phone_fields:
                    phone_fields.append(field_info)
                break

    # 3. Check for labels containing phone-related text
    labels = soup.find_all('label')
    for label in labels:
        label_text = label.get_text().lower()
        for keyword in PHONE_KEYWORDS:
            if keyword in label_text:
                # Find associated input
                for_attr = label.get('for', '')
                if for_attr:
                    associated_input = soup.find('input', {'id': for_attr})
                    if associated_input:
                        field_info = {
                            'type': 'input[label match]',
                            'name': associated_input.get('name', ''),
                            'id': associated_input.get('id', ''),
                            'placeholder': associated_input.get('placeholder', ''),
                            'detection': f'label: {keyword}'
                        }
                        if field_info not in phone_fields:
                            phone_fields.append(field_info)
                break

    # 4. Check for common form builders and embedded forms
    # HubSpot forms
    if soup.find(class_=re.compile(r'hs-form|hbspt-form|hubspot')):
        # HubSpot forms often have phone fields
        hs_inputs = soup.find_all(class_=re.compile(r'hs-input'))
        for inp in hs_inputs:
            name = (inp.get('name', '') or '').lower()
            if 'phone' in name or 'mobile' in name:
                phone_fields.append({
                    'type': 'hubspot form',
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                    'placeholder': '',
                    'detection': 'HubSpot form'
                })

    # Typeform embeds
    if soup.find(attrs={'data-tf-widget': True}) or 'typeform' in html_content.lower():
        phone_fields.append({
            'type': 'typeform embed',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'Typeform detected (likely has phone field)'
        })

    # Calendly embeds (often request phone)
    if 'calendly' in html_content.lower():
        phone_fields.append({
            'type': 'calendly embed',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'Calendly detected (may request phone)'
        })

    # 5. Check for phone number patterns in form-related JavaScript
    phone_patterns = [
        r'phone[_\-]?number',
        r'phoneNumber',
        r'phone[_\-]?field',
        r'mobile[_\-]?number',
        r'mobileNumber',
        r'tel[_\-]?number',
        r'"phone"',
        r"'phone'",
        r'name=["\']phone["\']',
        r'type=["\']tel["\']',
    ]

    for pattern in phone_patterns:
        if re.search(pattern, html_content, re.IGNORECASE):
            # Don't add duplicate if we already found fields
            if not phone_fields:
                phone_fields.append({
                    'type': 'javascript/code reference',
                    'name': '',
                    'id': '',
                    'placeholder': '',
                    'detection': f'Code pattern: {pattern}'
                })
            break

    return phone_fields, soup

def check_website_with_playwright(url, pages_to_check):
    """Use Playwright to check website with JavaScript rendering."""
    phone_fields = []
    description = ''
    pages_checked = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()

            for page_path in pages_to_check[:8]:  # Check up to 8 pages
                try:
                    full_url = urljoin(url, page_path)
                    page.goto(full_url, wait_until='networkidle', timeout=TIMEOUT)
                    pages_checked.append(page_path)

                    # Wait for dynamic content
                    page.wait_for_timeout(2000)

                    # Get page content after JS rendering
                    content = page.content()

                    # Check for phone fields
                    fields, soup = check_html_for_phone_fields(content)

                    # Get description from homepage
                    if page_path == '/' and not description:
                        description = extract_meta_description(soup)

                    if fields:
                        phone_fields.extend(fields)

                    # Try clicking CTA buttons to reveal forms
                    if not phone_fields:
                        for pattern in BUTTON_PATTERNS[:5]:  # Try first 5 patterns
                            try:
                                # Look for buttons/links with this text
                                button = page.locator(f'button:has-text("{pattern}"), a:has-text("{pattern}"), [role="button"]:has-text("{pattern}")').first
                                if button.is_visible(timeout=1000):
                                    button.click(timeout=3000)
                                    page.wait_for_timeout(2000)

                                    # Check again after click
                                    content = page.content()
                                    fields, _ = check_html_for_phone_fields(content)
                                    if fields:
                                        for f in fields:
                                            f['detection'] += f' (after clicking "{pattern}")'
                                        phone_fields.extend(fields)
                                        break
                            except:
                                continue

                    # If we found phone fields, we can stop
                    if phone_fields:
                        break

                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    continue

            browser.close()

    except Exception as e:
        return None, '', str(e)

    # Deduplicate phone fields
    unique_fields = []
    seen = set()
    for field in phone_fields:
        key = (field.get('name', ''), field.get('id', ''), field.get('type', ''))
        if key not in seen:
            seen.add(key)
            unique_fields.append(field)

    return unique_fields, description, None

def check_website_with_requests(url, pages_to_check):
    """Fallback: Use requests to check website (no JS rendering)."""
    phone_fields = []
    description = ''

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    for page_path in pages_to_check[:6]:
        try:
            full_url = urljoin(url, page_path)
            response = requests.get(full_url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()

            fields, soup = check_html_for_phone_fields(response.text)

            if page_path == '/' and not description:
                description = extract_meta_description(soup)

            if fields:
                phone_fields.extend(fields)
                break

        except:
            continue

    return phone_fields, description, None

def check_website(company_data):
    """Check a single website for phone fields."""
    company_name = company_data.get('company_name', '')
    website = company_data.get('website', '')

    result = {
        **company_data,
        'has_phone_field': False,
        'phone_field_details': [],
        'status': 'pending',
        'error': None,
        'scraped_description': '',
        'sellence_reasons': [],
        'detection_method': ''
    }

    url = normalize_url(website)
    if not url:
        result['status'] = 'error'
        result['error'] = 'Invalid URL'
        return result

    try:
        # Try Playwright first (better JS support)
        if PLAYWRIGHT_AVAILABLE:
            phone_fields, description, error = check_website_with_playwright(url, PAGES_TO_CHECK)
            result['detection_method'] = 'playwright'

            if error:
                # Fall back to requests
                phone_fields, description, _ = check_website_with_requests(url, PAGES_TO_CHECK)
                result['detection_method'] = 'requests (fallback)'
        else:
            phone_fields, description, _ = check_website_with_requests(url, PAGES_TO_CHECK)
            result['detection_method'] = 'requests'

        result['has_phone_field'] = len(phone_fields) > 0 if phone_fields else False
        result['phone_field_details'] = phone_fields or []
        result['scraped_description'] = description
        result['status'] = 'success'

        # Generate Sellence reasons
        industry = result.get('industry', result.get('Industry', ''))
        category = result.get('category', result.get('Category', ''))
        desc = result.get('description', description)
        result['sellence_reasons'] = get_sellence_reasons(industry, category, desc)

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)[:100]

    return result

def process_csv(file_content):
    """Process uploaded CSV and check all websites."""
    try:
        decoded = file_content.decode('utf-8-sig')
    except:
        decoded = file_content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)

    if not rows:
        return {'error': 'CSV file is empty'}

    headers = reader.fieldnames

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

    found_columns = {}
    for key, possible_names in column_mapping.items():
        for name in possible_names:
            if name in headers:
                found_columns[key] = name
                break

    if 'company_name' not in found_columns or 'website' not in found_columns:
        return {'error': f'Could not find required columns. Found: {headers}. Need company name and website columns.'}

    companies = []
    for row in rows:
        company_data = {
            'company_name': row.get(found_columns.get('company_name', ''), '').strip(),
            'website': row.get(found_columns.get('website', ''), '').strip(),
        }

        for key, col_name in found_columns.items():
            if key not in ['company_name', 'website']:
                company_data[key] = row.get(col_name, '').strip()

        for col in headers:
            if col not in [found_columns.get(k) for k in found_columns]:
                company_data[col] = row.get(col, '').strip()

        if company_data['company_name'] and company_data['website']:
            companies.append(company_data)

    if not companies:
        return {'error': 'No valid companies found in CSV'}

    # Check websites (reduced parallelism for Playwright)
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_website, company): company for company in companies}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    results.sort(key=lambda x: x['company_name'])

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

    output = io.StringIO()
    if filtered:
        priority_fields = ['company_name', 'website', 'industry', 'employees', 'revenue',
                          'description', 'scraped_description', 'location', 'has_phone_field',
                          'sellence_reasons', 'status', 'detection_method']

        all_fields = set()
        for r in filtered:
            all_fields.update(r.keys())

        fieldnames = [f for f in priority_fields if f in all_fields]
        fieldnames += sorted([f for f in all_fields if f not in priority_fields and f not in ['phone_field_details', 'error']])

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for r in filtered:
            row = {**r}
            if 'sellence_reasons' in row and isinstance(row['sellence_reasons'], list):
                row['sellence_reasons'] = ' | '.join(row['sellence_reasons'])
            writer.writerow(row)

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
    print(f"  Playwright available: {PLAYWRIGHT_AVAILABLE}")
    print(f"  Open http://localhost:{port} in your browser")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
