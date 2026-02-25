import fitz  # PyMuPDF
from src.models.raw_document import RawPDFDocument, TextBlock

class PDFParser:
    """Извлекает текст, шрифты и координаты из PDF."""
    
    def parse(self, pdf_path: str) -> RawPDFDocument:
        """
        Возвращает RawPDFDocument, заполненный данными.
        Заглушка: пока просто открывает файл.
        """
        doc = fitz.open(pdf_path)
        raw_doc = RawPDFDocument(pages=list(range(len(doc))))
        # TODO: реализовать извлечение блоков с шрифтами и координатами
        # Использовать doc.get_page_text(page, flags=fitz.TEXT_PRESERVE_IMAGES?) 
        # и page.get_text("dict") для получения детальной информации.
        return raw_doc