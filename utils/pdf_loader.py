import pypdf
import os

def load_pdf_text(filepath: str, max_pages: int = 15) -> str:
    """
    Extracts text from a PDF file.
    Args:
        filepath: Path to the PDF file.
        max_pages: Maximum number of pages to read (default 15 to avoid massive context).
    Returns:
        Extracted text as a string.
    """
    if not os.path.exists(filepath):
        return f"Error: File not found at {filepath}"
    
    try:
        reader = pypdf.PdfReader(filepath)
        text = ""
        # Read up to max_pages or total pages, whichever is smaller
        num_pages = len(reader.pages)
        pages_to_read = min(num_pages, max_pages)
        
        print(f"Reading {pages_to_read} pages from {os.path.basename(filepath)}...")
        
        for i in range(pages_to_read):
            page = reader.pages[i]
            extracted = page.extract_text()
            if extracted:
                text += f"\n--- PAGE {i+1} ---\n{extracted}\n"
                
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
