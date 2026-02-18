import os
import pandas as pd
import pypdf

def load_data_context(filepath: str, max_pages: int = 20, max_rows: int = 100) -> str:
    """
    Unified loader for PDF, CSV, MD, TXT files.
    Returns a string representation of the content suitable for LLM context.
    
    Args:
        filepath: Path to the data file
        max_pages: Max pages for PDF
        max_rows: Max rows for CSV (to avoid context overflow)
    """
    if not os.path.exists(filepath):
        return f"Error: File not found at {filepath}"
        
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        # CSV Handling (Structured Data)
        if ext == '.csv':
            print(f"Loading CSV data from {filepath}...")
            df = pd.read_csv(filepath)
            
            # Context Optimization:
            # 1. Summary Statistics
            summary = df.describe().to_markdown()
            
            # 2. Data Preview (First & Last rows if large)
            if len(df) > max_rows:
                preview = pd.concat([df.head(max_rows // 2), df.tail(max_rows // 2)]).to_markdown(index=False)
                return f"### DATA DATASET SUMMARY (Statistics)\n{summary}\n\n### DATA SAMPLES (First/Last {max_rows} rows)\n{preview}\n"
            else:
                return f"### DATA DATASET\n{df.to_markdown(index=False)}\n"
                
        # Markdown / Text Handling (Reports)
        elif ext in ['.md', '.txt']:
            print(f"Loading Text data from {filepath}...")
            with open(filepath, 'r', encoding='utf-8') as f:
                return f"### ATTACHED REPORT CONTENT\n\n{f.read()}\n"
                
        # PDF Handling (Legacy)
        elif ext == '.pdf':
            print(f"Loading PDF data from {filepath}...")
            reader = pypdf.PdfReader(filepath)
            text = ""
            num_pages = len(reader.pages)
            pages_to_read = min(num_pages, max_pages)
            
            for i in range(pages_to_read):
                page = reader.pages[i]
                extracted = page.extract_text()
                if extracted:
                    text += f"\n--- PAGE {i+1} ---\n{extracted}\n"
            return f"### ATTACHED PDF EXTRACT\n\n{text}\n"
            
        else:
            return f"Error: Unsupported file extension {ext}"
            
    except Exception as e:
        return f"Error loading data file: {str(e)}"
