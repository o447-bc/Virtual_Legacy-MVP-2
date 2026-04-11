#!/usr/bin/env python3
"""
Convert patent filing .md files to properly formatted PDFs.
Uses fpdf2 for PDF generation and markdown for HTML parsing.

Output: US Letter, Times New Roman 12pt, 1-inch margins, 1.5 line spacing.
"""

import re
import os
import textwrap
from fpdf import FPDF

class PatentPDF(FPDF):
    """Custom PDF class for patent filings with embedded fonts."""
    
    def __init__(self):
        super().__init__(orientation='P', unit='pt', format='Letter')
        self.set_auto_page_break(auto=True, margin=72)
        self.page_num = 0
        
        # Register Times New Roman TTF fonts (embedded in PDF)
        font_dir = '/System/Library/Fonts/Supplemental'
        self.add_font('TNR', '', os.path.join(font_dir, 'Times New Roman.ttf'), uni=True)
        self.add_font('TNR', 'B', os.path.join(font_dir, 'Times New Roman Bold.ttf'), uni=True)
        self.add_font('TNR', 'I', os.path.join(font_dir, 'Times New Roman Italic.ttf'), uni=True)
        self.add_font('TNR', 'BI', os.path.join(font_dir, 'Times New Roman Bold Italic.ttf'), uni=True)
        
        # Register Courier New TTF font (embedded in PDF)
        self.add_font('CNR', '', os.path.join(font_dir, 'Courier New.ttf'), uni=True)
        self.add_font('CNR', 'B', os.path.join(font_dir, 'Courier New Bold.ttf'), uni=True)
        
    def header(self):
        pass  # No header needed
    
    def footer(self):
        self.set_y(-50)
        self.set_font('TNR', '', 10)
        self.cell(0, 14, f'Page {self.page_no()}', align='C')

    def add_title_page_line(self, text, size=12, bold=False, align='C', spacing=18):
        style = 'B' if bold else ''
        self.set_font('TNR', style, size)
        self.multi_cell(0, spacing, text, align=align)
        self.ln(4)

    def add_heading(self, text, level=2):
        text = text.encode('latin-1', errors='replace').decode('latin-1')
        if level == 1:
            self.set_font('TNR', 'B', 14)
            self.ln(8)
            self.multi_cell(0, 20, text, align='C')
            self.ln(6)
        elif level == 2:
            self.set_font('TNR', 'B', 12)
            self.ln(6)
            self.multi_cell(0, 18, text, align='L')
            self.ln(2)
        elif level == 3:
            self.set_font('TNR', 'B', 12)
            self.ln(4)
            self.multi_cell(0, 18, text, align='L')
            self.ln(2)
        elif level == 4:
            self.set_font('TNR', 'BI', 12)
            self.ln(2)
            self.multi_cell(0, 18, text, align='L')
            self.ln(2)

    def add_paragraph(self, text, indent=True):
        text = text.encode('latin-1', errors='replace').decode('latin-1')
        self.set_font('TNR', '', 12)
        if indent:
            # First line indent
            self.set_x(self.l_margin + 36)
            w = self.w - self.l_margin - self.r_margin - 36
        else:
            w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 18, text, align='J')
        self.ln(2)

    def add_code_block(self, text):
        self.set_font('CNR', '', 7)
        self.ln(4)
        # Clean unicode in code blocks too
        text = text.replace('\u2014', '--')
        text = text.replace('\u2013', '-')
        text = text.replace('\u2018', "'")
        text = text.replace('\u2019', "'")
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        text = text.replace('\u2192', '->')
        text = text.replace('\u2190', '<-')
        text = text.replace('\u25cf', 'o')
        text = text.replace('\u2022', '-')
        text = text.replace('\u2713', '[x]')
        text = text.replace('\u25b6', '>')
        text = text.replace('\u25bc', 'v')
        text = text.replace('\u2500', '-')
        text = text.replace('\u2502', '|')
        text = text.replace('\u250c', '+')
        text = text.replace('\u2510', '+')
        text = text.replace('\u2514', '+')
        text = text.replace('\u2518', '+')
        text = text.replace('\u251c', '+')
        text = text.replace('\u2524', '+')
        text = text.replace('\u252c', '+')
        text = text.replace('\u2534', '+')
        text = text.replace('\u253c', '+')
        text = text.replace('\u2580', '=')
        text = text.replace('\u2584', '=')
        text = text.replace('\u2588', '#')
        text = text.replace('\u2591', '.')
        text = text.replace('\u2592', ':')
        text = text.replace('\u2593', '#')
        text = text.replace('\u25a0', '#')
        text = text.replace('\u25a1', '[ ]')
        text = text.replace('\u25b2', '^')
        text = text.replace('\u25bc', 'v')
        text = text.replace('\u25c4', '<')
        text = text.replace('\u25ba', '>')
        text = text.replace('\u2605', '*')
        text = text.replace('\u2606', '*')
        text = text.encode('latin-1', errors='replace').decode('latin-1')
        lines = text.split('\n')
        for line in lines:
            if len(line) > 95:
                line = line[:95]
            self.cell(0, 9, '  ' + line)
            self.ln(9)
        self.ln(4)
        self.set_font('TNR', '', 12)

    def add_claim(self, number, text):
        text = text.encode('latin-1', errors='replace').decode('latin-1')
        self.set_font('TNR', '', 12)
        self.ln(4)
        # Claim number
        claim_prefix = f"{number}. "
        self.set_x(self.l_margin)
        self.multi_cell(0, 18, claim_prefix + text, align='J')
        self.ln(4)

    def add_table_row(self, cells, widths, bold=False):
        style = 'B' if bold else ''
        self.set_font('TNR', style, 10)
        x_start = self.l_margin
        h = 14
        for i, (cell, w) in enumerate(zip(cells, widths)):
            self.set_x(x_start)
            self.cell(w, h, cell, border=1)
            x_start += w
        self.ln(h)

def parse_and_render(pdf, md_text):
    """Parse markdown text and render to PDF."""
    lines = md_text.split('\n')
    i = 0
    in_code_block = False
    code_buffer = []
    in_claim_section = False
    
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End code block
                pdf.add_code_block('\n'.join(code_buffer))
                code_buffer = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue
        
        # Skip horizontal rules
        if line.strip() == '---':
            i += 1
            continue
        
        # Skip empty lines
        if not line.strip():
            i += 1
            continue
        
        # Headings
        if line.startswith('# ') and not line.startswith('# PROVISIONAL'):
            text = line[2:].strip()
            pdf.add_heading(text, level=1)
            i += 1
            continue
        if line.startswith('## '):
            text = line[3:].strip()
            if text in ('CLAIMS', 'ABSTRACT'):
                in_claim_section = (text == 'CLAIMS')
            pdf.add_heading(text, level=2)
            i += 1
            continue
        if line.startswith('### '):
            text = line[4:].strip()
            if 'Claim Set' in text:
                in_claim_section = True
            pdf.add_heading(text, level=3)
            i += 1
            continue
        if line.startswith('#### '):
            text = line[5:].strip()
            pdf.add_heading(text, level=4)
            i += 1
            continue
        
        # Skip the top-level title/header lines that are part of cover sheet
        if line.startswith('# PROVISIONAL'):
            i += 1
            continue
        
        # Table rows (simple handling)
        if line.strip().startswith('|'):
            # Skip separator rows
            if '---' in line:
                i += 1
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                # Simple rendering as text
                pdf.set_font('TNR', '', 11)
                row_text = '  |  '.join(cells)
                row_text = clean_markdown(row_text)
                pdf.set_x(pdf.l_margin + 18)
                pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 18, 16, row_text, align='L')
            i += 1
            continue
        
        # Paragraph numbers [0001] etc
        para_match = re.match(r'^\[(\d{4})\]\s*(.*)', line)
        if para_match:
            para_num = para_match.group(1)
            para_text = para_match.group(2)
            # Collect continuation lines
            while i + 1 < len(lines) and lines[i+1].strip() and not lines[i+1].startswith('[0') and not lines[i+1].startswith('#') and not lines[i+1].startswith('```') and not lines[i+1].startswith('|') and not lines[i+1].strip().startswith('---') and not re.match(r'^\d+\.', lines[i+1].strip()):
                i += 1
                para_text += ' ' + lines[i].strip()
            
            # Clean markdown formatting
            para_text = clean_markdown(para_text)
            
            pdf.set_font('TNR', '', 12)
            full_text = f"[{para_num}] {para_text}"
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 18, full_text, align='J')
            pdf.ln(2)
            i += 1
            continue
        
        # Numbered claims (1. A computer-implemented...)
        claim_match = re.match(r'^(\d+)\.\s+(.*)', line)
        if claim_match and in_claim_section:
            num = claim_match.group(1)
            claim_text = claim_match.group(2)
            # Collect continuation lines (indented or starting with -)
            while i + 1 < len(lines) and lines[i+1].strip() and not re.match(r'^\d+\.', lines[i+1].strip()) and not lines[i+1].startswith('#') and not lines[i+1].startswith('```') and not lines[i+1].strip().startswith('---'):
                i += 1
                next_line = lines[i].strip()
                if next_line.startswith('- '):
                    claim_text += '\n   ' + next_line
                else:
                    claim_text += ' ' + next_line
            
            claim_text = clean_markdown(claim_text)
            pdf.add_claim(num, claim_text)
            i += 1
            continue
        
        # Bullet points
        if line.strip().startswith('- '):
            text = line.strip()[2:]
            text = clean_markdown(text)
            pdf.set_font('TNR', '', 12)
            pdf.set_x(pdf.l_margin + 36)
            w = pdf.w - pdf.l_margin - pdf.r_margin - 36
            pdf.cell(14, 18, '-')  # bullet as dash (latin-1 safe)
            pdf.multi_cell(w - 14, 18, text, align='J')
            pdf.ln(1)
            i += 1
            continue
        
        # Regular text / label lines (like "Name: ..." or "Residence: ...")
        text = clean_markdown(line.strip())
        if text:
            pdf.add_paragraph(text, indent=False)
        i += 1


def clean_markdown(text):
    """Remove markdown formatting and replace Unicode with ASCII equivalents."""
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    # Links
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Unicode replacements for latin-1 compatibility
    text = text.replace('\u2014', '--')   # em dash
    text = text.replace('\u2013', '-')    # en dash
    text = text.replace('\u2018', "'")    # left single quote
    text = text.replace('\u2019', "'")    # right single quote
    text = text.replace('\u201c', '"')    # left double quote
    text = text.replace('\u201d', '"')    # right double quote
    text = text.replace('\u2026', '...')  # ellipsis
    text = text.replace('\u00d7', 'x')   # multiplication sign
    text = text.replace('\u2265', '>=')   # greater than or equal
    text = text.replace('\u2264', '<=')   # less than or equal
    text = text.replace('\u2192', '->')   # right arrow
    text = text.replace('\u2190', '<-')   # left arrow
    text = text.replace('\u2022', '-')    # bullet
    text = text.replace('\u25cf', '-')    # black circle
    text = text.replace('\u2713', '[x]')  # check mark
    text = text.replace('\u2717', '[ ]')  # cross mark
    text = text.replace('\u00b2', '2')    # superscript 2
    # Catch any remaining non-latin-1 characters
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    return text


def convert_file(md_path, pdf_path):
    """Convert a single .md file to PDF."""
    print(f"Converting: {md_path} -> {pdf_path}")
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    pdf = PatentPDF()
    pdf.set_margins(72, 72, 72)  # 1 inch = 72 points
    pdf.add_page()
    
    parse_and_render(pdf, md_text)
    
    pdf.output(pdf_path)
    
    file_size = os.path.getsize(pdf_path)
    print(f"  Created: {pdf_path} ({file_size:,} bytes, {pdf.page_no()} pages)")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_convert = [
        ('Filing_A_Platform.md', 'Filing_A_Platform.pdf'),
        ('Filing_B_Avatar.md', 'Filing_B_Avatar.pdf'),
        ('FILING_INSTRUCTIONS_CONSOLIDATED.md', 'FILING_INSTRUCTIONS_CONSOLIDATED.pdf'),
    ]
    
    for md_name, pdf_name in files_to_convert:
        md_path = os.path.join(script_dir, md_name)
        pdf_path = os.path.join(script_dir, pdf_name)
        
        if not os.path.exists(md_path):
            print(f"  SKIPPED: {md_name} not found")
            continue
        
        convert_file(md_path, pdf_path)
    
    print("\nDone. All PDFs created in:", script_dir)


if __name__ == '__main__':
    main()
