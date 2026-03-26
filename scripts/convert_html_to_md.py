#!/usr/bin/env python3
"""
Convert FootyStats API HTML documentation to Markdown format.
"""

import os
import re
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path


def extract_main_content(soup):
    """Extract the main content area from the HTML."""
    # Try to find the main content div
    content_div = soup.find('div', class_='content')
    if content_div:
        return content_div
    return soup.body


def convert_table_to_md(table_div):
    """Convert HTML table structure to Markdown table."""
    rows = []
    
    # Find all table_row elements
    table_rows = table_div.find_all('div', class_='table_row')
    
    if not table_rows:
        return ""
    
    # Extract headers
    headers = []
    header_divs = table_div.find_all('div', class_='table_heads')
    if header_divs:
        for header_div in header_divs:
            for child in header_div.children:
                if isinstance(child, str) or child.name == 'span':
                    text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
                    if text:
                        headers.append(text)
    
    # If no headers found, try first row
    if not headers and table_rows:
        first_row = table_rows[0]
        for child in first_row.children:
            if isinstance(child, str) or (hasattr(child, 'name') and child.name == 'div'):
                text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
                if text:
                    headers.append(text)
    
    # Extract data rows
    data_rows = []
    for row in table_rows:
        cells = []
        for child in row.children:
            if isinstance(child, str) or (hasattr(child, 'name') and child.name == 'div'):
                text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
                if text:
                    cells.append(text)
        if cells:
            data_rows.append(cells)
    
    # Build Markdown table
    if not headers:
        return ""
    
    md_table = "| " + " | ".join(headers) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in data_rows:
        # Pad row if needed
        while len(row) < len(headers):
            row.append("")
        md_table += "| " + " | ".join(row[:len(headers)]) + " |\n"
    
    return md_table


def convert_code_block(pre_tag):
    """Convert code block to Markdown code fence."""
    code_content = pre_tag.get_text()
    
    # Determine language
    parent = pre_tag.parent
    lang = "json"  # default
    if parent and parent.has_attr('class'):
        classes = ' '.join(parent['class'])
        if 'json' in classes:
            lang = "json"
        elif 'javascript' in classes or 'js' in classes:
            lang = "javascript"
        elif 'python' in classes:
            lang = "python"
        elif 'html' in classes:
            lang = "html"
    
    return f"```{lang}\n{code_content}\n```"


def process_element(element, level=0):
    """Recursively process HTML elements and convert to Markdown."""
    md_parts = []
    
    if not element:
        return ""
    
    # Process based on element type
    if hasattr(element, 'name'):
        tag_name = element.name
        
        # Handle headings
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text(strip=True)
            if text:
                prefix = '#' * int(tag_name[1])
                md_parts.append(f"\n{prefix} {text}\n")
        
        # Handle paragraphs
        elif tag_name == 'p':
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"{text}\n\n")
        
        # Handle code blocks
        elif tag_name == 'pre':
            code = convert_code_block(element)
            if code:
                md_parts.append(f"\n{code}\n\n")
        
        # Handle inline code
        elif tag_name == 'code':
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"`{text}` ")
        
        # Handle lists
        elif tag_name == 'ul':
            for li in element.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if text:
                    md_parts.append(f"- {text}\n")
            md_parts.append("\n")
        
        elif tag_name == 'ol':
            for idx, li in enumerate(element.find_all('li', recursive=False), 1):
                text = li.get_text(strip=True)
                if text:
                    md_parts.append(f"{idx}. {text}\n")
            md_parts.append("\n")
        
        # Handle tables (custom div structure)
        elif tag_name == 'div':
            classes = element.get('class', [])
            
            # Check if it's a table structure
            if 'data_table' in classes or 'table_contents' in classes:
                table_md = convert_table_to_md(element)
                if table_md:
                    md_parts.append(f"\n{table_md}\n")
            
            # Check if it's a code visualization block
            elif 'code_visualisation' in classes:
                pre_tag = element.find('pre')
                if pre_tag:
                    code = convert_code_block(pre_tag)
                    if code:
                        md_parts.append(f"\n{code}\n\n")
            
            # Check for infobox
            elif 'infobox' in classes:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n> ℹ️ {text}\n\n")
            
            # Process children for other divs
            else:
                for child in element.children:
                    if not isinstance(child, NavigableString):
                        result = process_element(child, level + 1)
                        if result:
                            md_parts.append(result)
        
        # Handle spans with meaningful content
        elif tag_name == 'span':
            # Only process if it has meaningful text and no complex children
            text = element.get_text(strip=True)
            if text and len(text) > 0:
                # Check if it's a button or interactive element
                if 'button' not in ' '.join(element.get('class', [])):
                    md_parts.append(f"{text} ")
        
        # Handle links
        elif tag_name == 'a':
            text = element.get_text(strip=True)
            href = element.get('href', '')
            if text and href:
                # Skip navigation links and javascript links
                if not href.startswith('javascript') and text not in ['Previous', 'Next', '↑', '↓']:
                    md_parts.append(f"[{text}]({href}) ")
        
        # Handle line breaks
        elif tag_name == 'br':
            md_parts.append("\n")
        
        # Recursively process other elements
        else:
            for child in element.children:
                if not isinstance(child, NavigableString):
                    result = process_element(child, level + 1)
                    if result:
                        md_parts.append(result)
    
    elif isinstance(element, str):
        # Handle text nodes
        text = element.strip()
        if text and len(text) > 0:
            # Filter out common noise
            noise_patterns = ['Copy', 'Show↓', 'Hide ↑', 'Copied']
            if not any(noise in text for noise in noise_patterns):
                md_parts.append(f"{text} ")
    
    return ''.join(md_parts)


def clean_markdown(md_content):
    """Clean up the Markdown content."""
    # Remove multiple consecutive newlines
    md_content = re.sub(r'\n{3,}', '\n\n', md_content)
    
    # Remove trailing whitespace
    lines = [line.rstrip() for line in md_content.split('\n')]
    md_content = '\n'.join(lines)
    
    # Remove empty lines at start and end
    md_content = md_content.strip()
    
    return md_content


def html_to_markdown(html_file_path):
    """Convert a single HTML file to Markdown."""
    print(f"Converting: {html_file_path}")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading {html_file_path}: {e}")
        return None
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style tags
    for tag in soup(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()
    
    # Remove navigation and footer
    for nav_class in ['navbar', 'nav-item', 'sidebar_documentation', 'landingFooter']:
        for tag in soup.find_all(class_=nav_class):
            tag.decompose()
    
    # Extract main content
    content_div = soup.find('div', class_='content')
    if not content_div:
        content_div = soup.body
    
    # Convert to Markdown
    md_content = process_element(content_div)
    
    # Clean up
    md_content = clean_markdown(md_content)
    
    # Add title at the top if available
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Remove " | Soccer Stats API" suffix
        title = title.replace(' | Soccer Stats API', '')
        md_content = f"# {title}\n\n{md_content}"
    
    return md_content


def main():
    """Main function to convert all HTML files."""
    # Get the directory
    script_dir = Path(__file__).parent
    html_files = list(script_dir.glob('*.html'))
    
    if not html_files:
        print("No HTML files found!")
        return
    
    print(f"Found {len(html_files)} HTML files to convert")
    
    # Convert each file
    for html_file in html_files:
        md_content = html_to_markdown(html_file)
        
        if md_content:
            # Create output filename
            md_filename = html_file.stem + '.md'
            md_path = script_dir / md_filename
            
            # Write Markdown file
            try:
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"✓ Created: {md_path}")
            except Exception as e:
                print(f"Error writing {md_path}: {e}")
    
    print(f"\nConversion complete!")


if __name__ == '__main__':
    main()
