#!/usr/bin/env python3
"""
Convert Goalcast HTML documentation to Markdown format.
专门处理带有表格和卡片的 HTML 文档。
"""

import sys
import re
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from pathlib import Path


def convert_table_to_md(table):
    """Convert HTML table to Markdown table."""
    rows = []
    
    # Get headers
    header_row = table.find('thead')
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
        if headers:
            rows.append("| " + " | ".join(headers) + " |")
            rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Get body
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
    else:
        # Table without tbody
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
    
    return "\n".join(rows) if rows else ""


def convert_badges_to_md(element):
    """Convert badge spans to Markdown badges."""
    badges = []
    for badge in element.find_all(class_=re.compile(r'badge')):
        text = badge.get_text(strip=True)
        if text:
            # Check badge color class
            classes = badge.get('class', [])
            if 'b-green' in classes or 'badge-req' in classes:
                badges.append(f"🟢 {text}")
            elif 'b-amber' in classes or 'badge-opt' in classes or 'badge-time' in classes:
                badges.append(f"🟡 {text}")
            elif 'b-red' in classes:
                badges.append(f"🔴 {text}")
            elif 'b-blue' in classes:
                badges.append(f"🔵 {text}")
            elif 'b-purple' in classes:
                badges.append(f"🟣 {text}")
            else:
                badges.append(f"⚪ {text}")
    return " ".join(badges) if badges else ""


def convert_field_cells_to_md(grid):
    """Convert field cells grid to Markdown list."""
    items = []
    for cell in grid.find_all(class_='field-cell'):
        name_elem = cell.find(class_='field-cell-name')
        key_elem = cell.find(class_='field-cell-key')
        note_elem = cell.find(class_='field-cell-note')
        
        if name_elem:
            name = name_elem.get_text(strip=True)
            key = key_elem.get_text(strip=True) if key_elem else ""
            note = note_elem.get_text(strip=True) if note_elem else ""
            
            item = f"- **{name}**"
            if key:
                item += f" `({key})`"
            if note:
                item += f" — {note}"
            items.append(item)
    
    return "\n".join(items) if items else ""


def convert_feasibility_to_md(block):
    """Convert feasibility assessment to Markdown."""
    lines = []
    title = block.find(class_='feasibility-title')
    if title:
        lines.append(f"#### {title.get_text(strip=True)}")
    
    for f_row in block.find_all(class_='f-row'):
        label = f_row.find(class_='f-label')
        score = f_row.find(class_='f-score')
        fill = f_row.find(class_='f-fill')
        
        if label and score:
            label_text = label.get_text(strip=True)
            score_text = score.get_text(strip=True)
            # Try to get percentage from style
            percentage = ""
            if fill and 'style' in fill.attrs:
                style = fill['style']
                match = re.search(r'width:(\d+)%', style)
                if match:
                    percentage = f" ({match.group(1)}%)"
            
            lines.append(f"- **{label_text}**: {score_text}{percentage}")
    
    # Get notes
    notes_block = block.find(class_='f-notes')
    if notes_block:
        lines.append("")
        for note in notes_block.find_all(class_='f-note'):
            note_text = note.get_text(strip=True)
            # Remove the "—" prefix that's added via CSS
            if note_text.startswith('—'):
                note_text = note_text[1:].strip()
            lines.append(f"  - {note_text}")
    
    return "\n".join(lines) if lines else ""


def convert_access_to_md(block):
    """Convert access method block to Markdown."""
    lines = []
    header = block.find(class_='access-header')
    if header:
        lines.append(f"#### {header.get_text(strip=True)}")
    
    body = block.find(class_='access-body')
    if body:
        for row in body.find_all(class_='access-row'):
            label = row.find(class_='access-row-label')
            val = row.find(class_='access-row-val')
            
            if label and val:
                label_text = label.get_text(strip=True)
                # Get text content but preserve code elements
                val_text = val.get_text(strip=True)
                # Find and preserve code elements
                code_elements = val.find_all('code')
                for code in code_elements:
                    code_text = code.get_text(strip=True)
                    val_text = val_text.replace(code_text, f"`{code_text}`")
                
                lines.append(f"- **{label_text}**: {val_text}")
    
    return "\n".join(lines) if lines else ""


def process_element(element, level=0):
    """Recursively process HTML elements and convert to Markdown."""
    md_parts = []
    
    if not element:
        return ""
    
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
        
        # Handle tables
        elif tag_name == 'table':
            table_md = convert_table_to_md(element)
            if table_md:
                md_parts.append(f"\n{table_md}\n\n")
        
        # Handle divs with specific classes
        elif tag_name == 'div':
            classes = element.get('class', [])
            
            # Page header
            if 'page-header' in classes:
                title = element.find('h1')
                desc = element.find('p')
                if title:
                    md_parts.append(f"# {title.get_text(strip=True)}\n\n")
                if desc:
                    md_parts.append(f"{desc.get_text(strip=True)}\n\n")
            
            # Section title
            elif 'section-title' in classes:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n## {text}\n")
            
            # Source section (main data source cards)
            elif 'source-section' in classes:
                # Process children
                for child in element.children:
                    # Skip NavigableString objects
                    if isinstance(child, NavigableString) or not hasattr(child, 'children'):
                        continue
                    result = process_element(child, level + 1)
                    if result:
                        md_parts.append(result)
            
            # Source header
            elif 'source-header' in classes:
                icon = element.find(class_='source-icon')
                name = element.find(class_='source-name')
                url = element.find(class_='source-url')
                desc = element.find(class_='source-desc')
                badges = element.find(class_='source-badges')
                
                if name:
                    md_parts.append(f"\n### {name.get_text(strip=True)}\n\n")
                if url:
                    md_parts.append(f"**URL**: {url.get_text(strip=True)}\n\n")
                if desc:
                    md_parts.append(f"{desc.get_text(strip=True)}\n\n")
                if badges:
                    badge_md = convert_badges_to_md(badges)
                    if badge_md:
                        md_parts.append(f"{badge_md}\n\n")
            
            # Fields section
            elif 'fields-section' in classes:
                for child in element.children:
                    # Skip NavigableString objects
                    if isinstance(child, NavigableString) or not hasattr(child, 'children'):
                        continue
                    result = process_element(child, level + 1)
                    if result:
                        md_parts.append(result)
            
            # Section label
            elif 'section-label' in classes:
                text = element.get_text(strip=True)
                if text:
                    md_parts.append(f"\n**{text}**\n")
            
            # Fields grid
            elif 'fields-grid' in classes:
                fields_md = convert_field_cells_to_md(element)
                if fields_md:
                    md_parts.append(f"\n{fields_md}\n\n")
            
            # Access block
            elif 'access-block' in classes:
                access_md = convert_access_to_md(element)
                if access_md:
                    md_parts.append(f"\n{access_md}\n\n")
            
            # Feasibility block
            elif 'feasibility-block' in classes:
                feasibility_md = convert_feasibility_to_md(element)
                if feasibility_md:
                    md_parts.append(f"\n{feasibility_md}\n\n")
            
            # Overview wrap
            elif 'overview-wrap' in classes:
                table = element.find('table')
                if table:
                    table_md = convert_table_to_md(table)
                    if table_md:
                        md_parts.append(f"\n{table_md}\n\n")
            
            # Legend
            elif 'legend' in classes:
                md_parts.append("\n**图例**:\n")
                for leg_item in element.find_all(class_='leg-item'):
                    text = leg_item.get_text(strip=True)
                    if text:
                        md_parts.append(f"- {text}\n")
                md_parts.append("\n")
            
            # Summary grid
            elif 'summary-grid' in classes:
                md_parts.append("\n**数据汇总**:\n")
                for card in element.find_all(class_='summary-card'):
                    num = card.find(class_='summary-num')
                    label = card.find(class_='summary-label')
                    if num and label:
                        md_parts.append(f"- **{num.get_text(strip=True)}** {label.get_text(strip=True)}\n")
                md_parts.append("\n")
            
            # Recommended stack table
            elif 'recommended-stack' in str(classes):
                table = element.find('table')
                if table:
                    table_md = convert_table_to_md(table)
                    if table_md:
                        md_parts.append(f"\n{table_md}\n\n")
            
            # Process children for other divs
            else:
                for child in element.children:
                    # Skip NavigableString objects and elements without children attribute
                    if isinstance(child, NavigableString) or not hasattr(child, 'children'):
                        continue
                    result = process_element(child, level + 1)
                    if result:
                        md_parts.append(result)
        
        # Handle hr (horizontal rules)
        elif tag_name == 'hr':
            md_parts.append("\n---\n\n")
        
        # Handle code
        elif tag_name == 'code':
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"`{text}` ")
        
        # Handle strong/bold
        elif tag_name in ['strong', 'b']:
            text = element.get_text(strip=True)
            if text:
                md_parts.append(f"**{text}** ")
        
        # Recursively process other elements
        else:
            for child in element.children:
                # Skip NavigableString objects and elements without children attribute
                if isinstance(child, NavigableString) or not hasattr(child, 'children'):
                    continue
                result = process_element(child, level + 1)
                if result:
                    md_parts.append(result)
    
    elif isinstance(element, str):
        text = element.strip()
        if text and len(text) > 0:
            # Filter out common noise
            noise_patterns = ['//', '→']
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


def html_to_markdown(html_file_path, output_path=None):
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
    
    # Remove sidebar and navigation
    for nav_class in ['sidebar', 'nav-item', 'nav-group']:
        for tag in soup.find_all(class_=nav_class):
            tag.decompose()
    
    # Extract main content
    main = soup.find('main')
    if not main:
        main = soup.body
    
    # Convert to Markdown
    md_content = process_element(main)
    
    # Clean up
    md_content = clean_markdown(md_content)
    
    # Add title at the top if available
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Remove " — Goalcast AI" suffix
        title = title.replace(' — Goalcast AI', '').replace(' — Goalcast', '')
        md_content = f"# {title}\n\n{md_content}"
    
    # Write to file if output path provided
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"✓ Created: {output_path}")
        except Exception as e:
            print(f"Error writing {output_path}: {e}")
    
    return md_content


def main():
    """Main function to convert specified HTML files."""
    if len(sys.argv) < 2:
        print("Usage: python convert_goalcast_html.py <html_file> [output_dir]")
        sys.exit(1)
    
    html_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not output_dir:
        # Default to doc directory
        output_dir = Path(html_file).parent.parent / 'doc'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert the file
    md_content = html_to_markdown(html_file)
    
    if md_content:
        # Create output filename
        md_filename = Path(html_file).stem + '.md'
        md_path = output_dir / md_filename
        
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
