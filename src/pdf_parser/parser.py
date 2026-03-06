import fitz  # PyMuPDF

class PDFParser:
    """Извлекает текст, шрифты и координаты из PDF."""
    
    def parse(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        all_pages_dict = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_dict = page.get_text("dict");
            all_pages_dict.append(page_dict)
        return all_pages_dict