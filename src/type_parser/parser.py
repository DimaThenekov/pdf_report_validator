from src.models.raw_document import RawPDFDocument
from src.models.structured_document import StructuredDocument

class TypeParser:
    """Преобразует сырой документ в структурированный, определяет тип практики."""
    
    def parse(self, raw_doc: RawPDFDocument) -> StructuredDocument:
        """
        Анализирует титульный лист и структуру, выделяет заголовки и параграфы,
        определяет тип практики (бакалавр/магистр).
        """
        # TODO: реализовать
        structured = StructuredDocument()
        return structured