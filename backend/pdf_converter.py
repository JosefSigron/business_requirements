"""
Simple PDF to TXT converter for licensing requirements processing.
Converts Hebrew PDF documents to clean TXT format for easier parsing.
"""

import pdfplumber
import os
from pathlib import Path
from typing import Optional
from bidi.algorithm import get_display


def pdf_to_txt(pdf_path: str, txt_path: Optional[str] = None) -> str:
    """
    Convert PDF file to TXT format.
    
    Args:
        pdf_path: Path to the source PDF file
        txt_path: Path for output TXT file (optional, defaults to same name with .txt extension)
        
    Returns:
        Path to the created TXT file
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: If PDF processing fails
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Default output path: same name as PDF but with .txt extension
    if txt_path is None:
        txt_path = pdf_path.with_suffix('.txt')
    else:
        txt_path = Path(txt_path)
    
    print(f"Converting PDF to TXT: {pdf_path} -> {txt_path}")
    
    try:
        extracted_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Processing {len(pdf.pages)} pages...")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"Processing page {page_num}...")
                
                # Extract text from page
                text = page.extract_text()

                if text:
                    # Normalize and split to lines for RTL handling
                    lines = [l.strip() for l in (text.replace('\r\n', '\n').replace('\r', '\n')).split('\n')]
                    for line in lines:
                        if not line:
                            extracted_text.append('\n')
                            continue
                        # If the line contains Hebrew chars, reorder visually (RTL)
                        if any('\u0590' <= ch <= '\u05FF' for ch in line):
                            line = get_display(line)
                        extracted_text.append(line)
                        extracted_text.append('\n')
        
        # Join all text and clean up
        full_text = ''.join(extracted_text)
        
        # Basic cleanup for Hebrew text
        full_text = full_text.replace('\r\n', '\n')  # Normalize line endings
        full_text = full_text.replace('\r', '\n')
        
        # Remove excessive blank lines but preserve paragraph structure
        lines = full_text.split('\n')
        cleaned_lines = []
        previous_empty = False
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
                previous_empty = False
            else:
                if not previous_empty:
                    cleaned_lines.append('')
                previous_empty = True
        
        final_text = '\n'.join(cleaned_lines)
        
        # Write to TXT file with UTF-8 encoding to support Hebrew
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
        
        print(f"✅ Conversion completed successfully!")
        print(f"📄 Output file: {txt_path}")
        print(f"📊 Extracted {len(final_text)} characters from {len(pdf.pages)} pages")
        
        return str(txt_path)
        
    except Exception as e:
        print(f"❌ Error during PDF conversion: {e}")
        raise


def main():
    """
    Command line interface for PDF conversion.
    Usage: python pdf_converter.py
    """
    import sys
    
    # Default paths for the licensing project
    default_pdf = "../18-07-2022_4.2A.pdf"
    default_txt = "../18-07-2022_4.2A.txt"
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        txt_path = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        pdf_path = default_pdf
        txt_path = default_txt
    
    try:
        result_path = pdf_to_txt(pdf_path, txt_path)
        print(f"\n🎉 PDF successfully converted to: {result_path}")
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print(f"💡 Make sure the PDF file exists: {pdf_path}")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
