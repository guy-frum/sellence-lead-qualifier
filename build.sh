#!/usr/bin/env bash
# Build script for Render.com

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium
