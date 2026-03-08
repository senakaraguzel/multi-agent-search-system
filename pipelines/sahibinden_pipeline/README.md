# Sahibinden Data Scraping Pipeline

## Purpose

This pipeline collects structured data from Sahibinden.com listings.

The system extracts listing information and converts it into structured metadata.

## Extracted Data

- Listing title
- Price
- Location
- Listing date
- Seller information
- Listing URL

## Pipeline Steps

1. Send search query to Sahibinden
2. Collect listing URLs from result pages
3. Visit each listing page
4. Extract metadata
5. Store results in JSON format

## Output Format

Example output:

{
  "title": "Satılık 2+1 Daire",
  "price": "3.200.000 TL",
  "location": "İstanbul / Şişli",
  "date": "2026-02-01",
  "seller": "Emlak Ofisi",
  "url": "https://www.sahibinden.com/..."
}

## Technologies

- Python
- BeautifulSoup / Selenium
- JSON data processing
