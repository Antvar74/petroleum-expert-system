from utils.pdf_loader import load_pdf_text

pdf_path = "data/INFORME GERENCIAL EJECUTIVO.pdf"
print(f"Checking {pdf_path}...")
text = load_pdf_text(pdf_path, max_pages=5)
print(f"Extracted {len(text)} characters.")
print("Sample:\n" + text[:200])
