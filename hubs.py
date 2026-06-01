#!/usr/bin/env python3
"""
Account Hubs for Sellence.

An account hub is a single-page briefing for a high-value target account:
company overview, why Sellence fits, the live phone-field qualification
signal, and the decision-makers worth reaching out to.

Add a new hub by appending an entry to HUBS keyed by its URL slug.
"""

HUBS = {
    'tal': {
        'slug': 'tal',
        'company_name': 'TAL',
        'tagline': "Australia's leading life insurance specialist",
        'website': 'tal.com.au',
        'linkedin': 'https://www.linkedin.com/company/talaustralia',
        'logo_url': 'https://logo.clearbit.com/tal.com.au',
        'industry': 'Life Insurance',
        'employees': '2,788',
        'revenue': '$500M – $1B',
        'location': 'Sydney, NSW, Australia',
        'founded': '1869 (150+ years)',
        'parent': 'Dai-ichi Life Group',
        'description': (
            "TAL is Australia's leading life insurance specialist. For over 150 years TAL has "
            "been protecting people, not things. Together with its partners, TAL insures more "
            "than 5 million customers and offers life insurance through three channels: direct "
            "to consumer, through a financial adviser, and via group and workplace "
            "superannuation schemes. TAL is part of the Dai-ichi Life Group, one of the "
            "world's largest insurance groups."
        ),
        # Why this account is a strong Sellence fit
        'fit_score': 'High',
        'signals': [
            "Runs a direct-to-consumer channel at tal.com.au with online quote forms that capture phone numbers — the core Sellence trigger.",
            "Life insurance is a complex, considered purchase: an instant human callback while the prospect is still on the quote page lifts quote-to-policy conversion.",
            "5M+ customers across three channels — the direct channel is exactly where speed-to-lead drives new business.",
            "Competes with AIA, Zurich and MLC for online shoppers, where responding in seconds rather than hours is a real differentiator.",
        ],
        'value_props': [
            "Call quote-form leads while they're still on the website, instead of hours later",
            "Build trust on a high-consideration product through immediate personal contact",
            "Answer complex coverage questions in real time to reduce quote abandonment",
            "Capture comparison shoppers before they leave for AIA, Zurich or MLC",
        ],
        # Curated decision-makers (sourced via Sellence enrichment).
        # role: 'champion' (owns the funnel / would feel the pain) or 'sponsor' (exec air cover)
        'contacts': [
            {
                'name': 'Michael Nixon',
                'title': 'Head of Digital and CRM',
                'linkedin': 'https://www.linkedin.com/in/michael-nixon-73920a44/',
                'role': 'champion',
                'angle': 'Owns the digital funnel and CRM — speed-to-lead on quote forms is squarely his metric.',
            },
            {
                'name': 'Ben Hannasky',
                'title': 'Head of Sales – Direct Growth Platform',
                'linkedin': 'https://www.linkedin.com/in/ben-hannasky-9a45b8b8/',
                'role': 'champion',
                'angle': 'Runs the direct (D2C) sales engine — instant callbacks convert directly into his new-business numbers.',
            },
            {
                'name': 'Shane Bennett',
                'title': 'Head of Digital Propositions',
                'linkedin': 'https://www.linkedin.com/in/shane-bennett-793969b1/',
                'role': 'champion',
                'angle': 'Shapes the online quote journey where the phone-capture form lives.',
            },
            {
                'name': 'Jen-Kui Maxwell',
                'title': 'Head of Marketing and Innovation',
                'linkedin': 'https://www.linkedin.com/in/jen-kui-maxwell-76165452/',
                'role': 'champion',
                'angle': 'Owns demand gen — cares about every quote form that converts rather than drops off.',
            },
            {
                'name': 'Jonathan Kelly',
                'title': 'Head of Growth & Partnerships',
                'linkedin': 'https://www.linkedin.com/in/jonathanckelly/',
                'role': 'champion',
                'angle': 'Growth mandate that maps directly to lifting quote-to-policy conversion.',
            },
            {
                'name': 'Beau Riley',
                'title': 'General Manager, Retail Sales & New Business',
                'linkedin': 'https://www.linkedin.com/in/beauriley/',
                'role': 'sponsor',
                'angle': 'Carries the retail new-business target — the budget owner for a conversion lift.',
            },
            {
                'name': 'James Henry Bagley',
                'title': 'Director – Consumer',
                'linkedin': 'https://www.linkedin.com/in/james-henry-bagley-859a211/',
                'role': 'sponsor',
                'angle': 'Executive over the consumer / direct line of business.',
            },
            {
                'name': 'Hayley Weston',
                'title': 'Head of Digital Partnerships',
                'linkedin': 'https://www.linkedin.com/in/hayley-weston-0a19a238/',
                'role': 'champion',
                'angle': 'Owns digital partnership channels that feed the online quote funnel.',
            },
        ],
    },
}


def get_hub(slug):
    """Return the hub dict for a slug, or None."""
    return HUBS.get(slug)


def list_hubs():
    """Return all hubs as a list for the index page."""
    return list(HUBS.values())
