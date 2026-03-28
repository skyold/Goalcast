#!/usr/bin/env python3
"""
Convert FootyStats API HTML documentation to Markdown format.
Enhanced version to ensure no information loss.
"""

import os
import re
from bs4 import BeautifulSoup, NavigableString, Comment
from pathlib import Path


def extract_main_content(soup):
    """Extract the main content area from the HTML."""
    content_div = soup.find('div', class_='content')
    if content_div:
        return content_div
    return soup.body


def convert_table_to_md(table_div):
    """Convert HTML table structure to Markdown table."""
    rows = []
    
    table_rows = table_div.find_all('div', class_='table_row')
    
    if not table_rows:
        return ""
    
    headers = []
    header_divs = table_div.find_all('div', class_='table_heads')
    if header_divs:
        for header_div in header_divs:
            for child in header_div.children:
                if isinstance(child, str) or child.name == 'span':
                    text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
                    if text:
                        headers.append(text)
    
    if not headers and table_rows:
        first_row = table_rows[0]
        for child in first_row.children:
            if isinstance(child, str) or (hasattr(child, 'name') and child.name == 'div'):
                text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
                if text:
                    headers.append(text)
    
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
    
    if not headers:
        return ""
    
    md_table = "| " + " | ".join(headers) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in data_rows:
        while len(row) < len(headers):
            row.append("")
        md_table += "| " + " | ".join(row[:len(headers)]) + " |\n"
    
    return md_table


def convert_code_block(pre_tag):
    """Convert code block to Markdown code fence."""
    code_content = pre_tag.get_text()
    
    parent = pre_tag.parent
    lang = "json"
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
    
    if hasattr(element, 'name'):
        tag_name = element.name
        
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text(strip=True)
            if text:
                prefix = '#' * int(tag_name[1])
                md_parts.append(f"\n{prefix} {text}\n")
        
        elif tag_name == 'p':
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"{text}\n\n")
        
        elif tag_name == 'div':
            classes = element.get('class', [])
            class_str = ' '.join(classes) if classes else ''
            
            if 'data_table' in classes or 'table_contents' in classes:
                table_md = convert_table_to_md(element)
                if table_md:
                    md_parts.append(f"\n{table_md}\n")
            
            elif 'code_visualisation' in classes:
                pre_tag = element.find('pre')
                if pre_tag:
                    code = convert_code_block(pre_tag)
                    if code:
                        md_parts.append(f"\n{code}\n\n")
            
            elif 'infobox' in classes:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n> ℹ️ {text}\n\n")
            
            elif 'head' in classes:
                for child in element.children:
                    if not isinstance(child, NavigableString):
                        result = process_element(child, level + 1)
                        if result:
                            md_parts.append(result)
            
            elif 'subtitle' in classes:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n### {text}\n")
            
            elif 'row' in classes:
                link = element.find('a')
                if link:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and href:
                        md_parts.append(f"- [{text}]({href})\n")
            
            elif 'code_prev' in classes or 'prev' in classes:
                for child in element.children:
                    if not isinstance(child, NavigableString):
                        result = process_element(child, level + 1)
                        if result:
                            md_parts.append(result)
            
            elif 'get_line' in classes:
                code_elem = element.find('code')
                if code_elem:
                    text = code_elem.get_text(strip=True)
                    if text:
                        md_parts.append(f"\n`{text}`\n\n")
                else:
                    text = element.get_text(strip=True)
                    if text:
                        md_parts.append(f"{text}\n\n")
            
            elif 'success_response' in class_str:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n> ✅ {text}\n\n")
            
            elif 'tablist' in class_str:
                pass
            
            elif 'hidebutton' in class_str or 'copybutton' in class_str or 'showbutton' in class_str:
                pass
            
            elif 'fl' in classes or 'fr' in classes or 'cf' in classes or 'w100' in classes or 'mt20' in classes or 'lh24' in classes or 'lh26' in classes or 'pb15' in classes or 'bbox' in classes or 'col-lg-9' in classes or 'col-sm-12' in classes:
                for child in element.children:
                    if not isinstance(child, NavigableString):
                        result = process_element(child, level + 1)
                        if result:
                            md_parts.append(result)
            
            else:
                for child in element.children:
                    if not isinstance(child, NavigableString):
                        result = process_element(child, level + 1)
                        if result:
                            md_parts.append(result)
        
        elif tag_name == 'pre':
            code = convert_code_block(element)
            if code:
                md_parts.append(f"\n{code}\n\n")
        
        elif tag_name == 'code':
            if element.parent and element.parent.name == 'pre':
                pass
            else:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"`{text}` ")
        
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
        
        elif tag_name == 'li':
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"- {text}\n")
        
        elif tag_name == 'span':
            if 'success_response' in ' '.join(element.get('class', [])):
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n> ✅ {text}\n\n")
            elif 'blue_color' in ' '.join(element.get('class', [])):
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"`{text}` ")
            else:
                text = element.get_text(strip=True)
                if text and len(text) > 0:
                    if 'button' not in ' '.join(element.get('class', [])):
                        md_parts.append(f"{text} ")
        
        elif tag_name == 'a':
            text = element.get_text(strip=True)
            href = element.get('href', '')
            if text and href:
                if not href.startswith('javascript') and text not in ['Previous', 'Next', '↑', '↓']:
                    md_parts.append(f"[{text}]({href}) ")
        
        elif tag_name == 'br':
            md_parts.append("\n")
        
        elif tag_name in ['strong', 'b']:
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"**{text}** ")
        
        elif tag_name in ['em', 'i']:
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"*{text}* ")
        
        elif tag_name == 'blockquote':
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"\n> {text}\n\n")
        
        else:
            for child in element.children:
                if not isinstance(child, NavigableString):
                    result = process_element(child, level + 1)
                    if result:
                        md_parts.append(result)
    
    elif isinstance(element, str):
        text = element.strip()
        if text and len(text) > 0:
            noise_patterns = ['Copy', 'Show↓', 'Hide ↑', 'Copied']
            if not any(noise in text for noise in noise_patterns):
                md_parts.append(f"{text} ")
    
    return ''.join(md_parts)


def clean_markdown(md_content):
    """Clean up the Markdown content."""
    md_content = re.sub(r'\n{3,}', '\n\n', md_content)
    
    lines = [line.rstrip() for line in md_content.split('\n')]
    md_content = '\n'.join(lines)
    
    md_content = md_content.strip()
    
    md_content = re.sub(r'  +', ' ', md_content)
    
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
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for tag in soup(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()
    
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    for nav_class in ['navbar', 'nav-item', 'sidebar_documentation', 'landingFooter', 'nav-tabs']:
        for tag in soup.find_all(class_=nav_class):
            tag.decompose()
    
    content_div = soup.find('div', class_='content')
    if not content_div:
        content_div = soup.body
    
    md_content = process_element(content_div)
    
    md_content = clean_markdown(md_content)
    
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        title = title.replace(' | Soccer Stats API', '')
        md_content = f"# {title}\n\n{md_content}"
    
    return md_content


def main():
    """Main function to convert all HTML files."""
    html_dir = Path("/Users/zhengningdai/workspace/skyold/Goalcast/doc/footystats")
    output_dir = html_dir / "md_output"
    
    if not html_dir.exists():
        print(f"Error: Directory does not exist: {html_dir}")
        return
    
    output_dir.mkdir(exist_ok=True)
    
    html_files = list(html_dir.glob("*.html"))
    
    if not html_files:
        print(f"No HTML files found in {html_dir}")
        return
    
    print(f"Found {len(html_files)} HTML files to convert")
    print(f"Output directory: {output_dir}")
    print("-" * 50)
    
    for html_file in sorted(html_files):
        md_content = html_to_markdown(html_file)
        
        if md_content:
            md_filename = html_file.stem + '.md'
            md_path = output_dir / md_filename
            
            try:
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"✓ Created: {md_path.name}")
                
                html_size = html_file.stat().st_size
                md_size = md_path.stat().st_size
                print(f"  HTML: {html_size:,} bytes -> MD: {md_size:,} bytes")
            except Exception as e:
                print(f"Error writing {md_path}: {e}")
        else:
            print(f"✗ Failed to convert: {html_file.name}")
    
    print("-" * 50)
    print(f"Conversion complete!")
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()
