#!/usr/bin/env python3
"""
Sellence Lead Qualifier - Web App
Upload a CSV of companies and check which ones collect phone numbers.
Enhanced detection patterns for better accuracy.
"""

from flask import Flask, render_template, request, jsonify, send_file
import csv
import io
import os
import re
import requests as req
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import json

app = Flask(__name__)

# Configuration
REQUEST_TIMEOUT = 15
MAX_WORKERS = 10
PHONE_KEYWORDS = ['phone', 'mobile', 'cell', 'tel', 'telephone', 'callback', 'call me', 'call-me', 'contact number']

# Extended list of pages to check (with and without trailing slashes)
PAGES_TO_CHECK = [
    '/',
    '/contact',
    '/contact/',
    '/contact-us',
    '/contact-us/',
    '/get-quote',
    '/get-quote/',
    '/quote',
    '/quote/',
    '/get-a-quote',
    '/get-a-quote/',
    '/free-quote',
    '/get-started',
    '/get-started/',
    '/start',
    '/signup',
    '/sign-up',
    '/register',
    '/demo',
    '/demo/',
    '/request-demo',
    '/book-demo',
    '/schedule',
    '/schedule/',
    '/talk-to-us',
    '/request-callback',
    '/apply',
    '/apply/',
    '/enroll',
    '/get-pricing',
    '/pricing',
    '/pricing/',
    '/plans',
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
    """Check HTML content for phone number input fields - ENHANCED VERSION."""
    soup = BeautifulSoup(html_content, 'html.parser')
    phone_fields = []

    # 0. Quick regex check for type="tel" or type='tel' in raw HTML (most reliable)
    if re.search(r'type=["\']tel["\']', html_content, re.IGNORECASE):
        phone_fields.append({
            'type': 'input[type=tel] (regex)',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'type=tel found in HTML'
        })

    # 1. Check input type="tel" (most reliable)
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
        if input_type in ['hidden', 'submit', 'button', 'checkbox', 'radio', 'file', 'image']:
            continue

        name = (inp.get('name', '') or '').lower()
        id_attr = (inp.get('id', '') or '').lower()
        placeholder = (inp.get('placeholder', '') or '').lower()
        aria_label = (inp.get('aria-label', '') or '').lower()
        class_attr = ' '.join(inp.get('class', [])).lower() if inp.get('class') else ''
        data_attrs = ' '.join([str(v) for k, v in inp.attrs.items() if k.startswith('data-')]).lower()

        combined = f"{name} {id_attr} {placeholder} {aria_label} {class_attr} {data_attrs}"

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
        label_text = label.get_text().lower().strip()
        for keyword in PHONE_KEYWORDS:
            if keyword in label_text:
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
                else:
                    # Label might wrap the input
                    nested_input = label.find('input')
                    if nested_input:
                        field_info = {
                            'type': 'input[nested in label]',
                            'name': nested_input.get('name', ''),
                            'id': nested_input.get('id', ''),
                            'placeholder': nested_input.get('placeholder', ''),
                            'detection': f'nested label: {keyword}'
                        }
                        if field_info not in phone_fields:
                            phone_fields.append(field_info)
                break

    # 4. Check for form field wrappers with phone text
    field_wrappers = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'field|input|form', re.I))
    for wrapper in field_wrappers:
        wrapper_text = wrapper.get_text().lower()[:100]
        for keyword in PHONE_KEYWORDS[:4]:  # Just main keywords
            if keyword in wrapper_text:
                nested_input = wrapper.find('input')
                if nested_input and nested_input.get('type', '').lower() not in ['hidden', 'submit', 'button']:
                    field_info = {
                        'type': 'input[wrapper text]',
                        'name': nested_input.get('name', ''),
                        'id': nested_input.get('id', ''),
                        'placeholder': nested_input.get('placeholder', ''),
                        'detection': f'wrapper: {keyword}'
                    }
                    if field_info not in phone_fields:
                        phone_fields.append(field_info)
                break

    # 5. Check for common form builders
    # HubSpot
    if soup.find(class_=re.compile(r'hs-form|hbspt-form|hubspot', re.I)) or 'hubspot' in html_content.lower():
        hs_inputs = soup.find_all(class_=re.compile(r'hs-input', re.I))
        for inp in hs_inputs:
            name = (inp.get('name', '') or '').lower()
            if any(k in name for k in ['phone', 'mobile', 'tel']):
                phone_fields.append({
                    'type': 'hubspot form',
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                    'placeholder': '',
                    'detection': 'HubSpot form field'
                })
        # HubSpot forms often have phone even if not visible in HTML
        if not phone_fields and 'hs-form' in html_content.lower():
            phone_fields.append({
                'type': 'hubspot form (likely)',
                'name': '',
                'id': '',
                'placeholder': '',
                'detection': 'HubSpot form detected (commonly includes phone)'
            })

    # Marketo
    if 'mktoForm' in html_content or 'marketo' in html_content.lower():
        phone_fields.append({
            'type': 'marketo form',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'Marketo form detected (commonly includes phone)'
        })

    # Pardot
    if 'pardot' in html_content.lower() or 'pi.pardot' in html_content:
        phone_fields.append({
            'type': 'pardot form',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'Pardot form detected (commonly includes phone)'
        })

    # Typeform
    if soup.find(attrs={'data-tf-widget': True}) or 'typeform.com' in html_content.lower():
        phone_fields.append({
            'type': 'typeform embed',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'Typeform detected (likely has phone field)'
        })

    # Calendly
    if 'calendly.com' in html_content.lower():
        phone_fields.append({
            'type': 'calendly embed',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'Calendly detected (may request phone)'
        })

    # JotForm
    if 'jotform' in html_content.lower():
        phone_fields.append({
            'type': 'jotform embed',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'JotForm detected (commonly includes phone)'
        })

    # Gravity Forms (WordPress) - enhanced detection
    if 'gform' in html_content.lower() or 'gravity-form' in html_content.lower() or 'gravityforms' in html_content.lower():
        # Check for gfield--type-phone class (Gravity Forms phone field)
        if 'gfield--type-phone' in html_content:
            phone_fields.append({
                'type': 'gravity form phone field',
                'name': '',
                'id': '',
                'placeholder': '',
                'detection': 'Gravity Forms phone field (gfield--type-phone)'
            })
        # Check for ginput_container_phone
        elif 'ginput_container_phone' in html_content:
            phone_fields.append({
                'type': 'gravity form phone field',
                'name': '',
                'id': '',
                'placeholder': '',
                'detection': 'Gravity Forms phone input (ginput_container_phone)'
            })
        # Generic Gravity Forms with phone input
        gf_phone = soup.find('input', {'type': 'tel'}) or soup.find(class_=re.compile(r'phone', re.I))
        if gf_phone or 'gfield_contains_required' in html_content:
            if not any('gravity' in f.get('type', '').lower() for f in phone_fields):
                phone_fields.append({
                    'type': 'gravity form',
                    'name': '',
                    'id': '',
                    'placeholder': '',
                    'detection': 'Gravity Forms detected'
                })

    # WPForms
    if 'wpforms' in html_content.lower():
        phone_fields.append({
            'type': 'wpforms',
            'name': '',
            'id': '',
            'placeholder': '',
            'detection': 'WPForms detected (commonly includes phone)'
        })

    # 6. Check for phone patterns in JavaScript/React code
    phone_code_patterns = [
        r'["\']phone["\']:\s*["\']',
        r'["\']phoneNumber["\']',
        r'["\']phone_number["\']',
        r'["\']mobileNumber["\']',
        r'["\']mobile_number["\']',
        r'name:\s*["\']phone["\']',
        r'id:\s*["\']phone["\']',
        r'field["\']:\s*["\']phone',
        r'type:\s*["\']tel["\']',
        r'"tel":\s*true',
        r'inputMode:\s*["\']tel["\']',
        r'phone.*required',
        r'required.*phone',
    ]

    for pattern in phone_code_patterns:
        if re.search(pattern, html_content, re.IGNORECASE):
            if not phone_fields:  # Only add if we haven't found anything else
                phone_fields.append({
                    'type': 'code pattern',
                    'name': '',
                    'id': '',
                    'placeholder': '',
                    'detection': f'JavaScript/React pattern detected'
                })
            break

    # 7. Check for phone validation patterns
    phone_validation_patterns = [
        r'phone.*validation',
        r'validate.*phone',
        r'phone.*regex',
        r'formatPhoneNumber',
        r'parsePhoneNumber',
        r'intl-tel-input',
        r'phone-input',
        r'PhoneInput',
        r'react-phone',
    ]

    for pattern in phone_validation_patterns:
        if re.search(pattern, html_content, re.IGNORECASE):
            if not any(f.get('detection', '').startswith('validation') for f in phone_fields):
                phone_fields.append({
                    'type': 'phone validation library',
                    'name': '',
                    'id': '',
                    'placeholder': '',
                    'detection': 'Phone validation/formatting library detected'
                })
            break

    # Deduplicate
    unique_fields = []
    seen = set()
    for field in phone_fields:
        key = (field.get('name', ''), field.get('id', ''), field.get('type', ''), field.get('detection', ''))
        if key not in seen:
            seen.add(key)
            unique_fields.append(field)

    return unique_fields, soup

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
        'pages_checked': 0
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
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    phone_fields = []
    description = ''
    pages_checked = 0

    for page_path in PAGES_TO_CHECK[:12]:  # Check up to 12 pages
        try:
            full_url = urljoin(url, page_path)
            response = req.get(full_url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)

            if response.status_code != 200:
                continue

            pages_checked += 1
            fields, soup = check_html_for_phone_fields(response.text)

            if page_path == '/' and not description:
                description = extract_meta_description(soup)

            if fields:
                phone_fields.extend(fields)
                # If we found strong evidence (type=tel or multiple indicators), stop
                strong_evidence = any(f['type'] == 'input[type=tel]' for f in fields)
                if strong_evidence or len(phone_fields) >= 2:
                    break

        except req.exceptions.Timeout:
            continue
        except req.exceptions.RequestException:
            continue
        except Exception:
            continue

    # Deduplicate final results
    unique_fields = []
    seen = set()
    for field in phone_fields:
        key = (field.get('name', ''), field.get('id', ''), field.get('type', ''))
        if key not in seen:
            seen.add(key)
            unique_fields.append(field)

    result['has_phone_field'] = len(unique_fields) > 0
    result['phone_field_details'] = unique_fields
    result['scraped_description'] = description
    result['pages_checked'] = pages_checked
    result['status'] = 'success' if pages_checked > 0 else 'error'
    if pages_checked == 0:
        result['error'] = 'Could not access website'

    # Generate Sellence reasons
    industry = result.get('industry', result.get('Industry', ''))
    category = result.get('category', result.get('Category', ''))
    desc = result.get('description', description)
    result['sellence_reasons'] = get_sellence_reasons(industry, category, desc)

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
                          'sellence_reasons', 'status', 'pages_checked']

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
    print(f"  Open http://localhost:{port} in your browser")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
