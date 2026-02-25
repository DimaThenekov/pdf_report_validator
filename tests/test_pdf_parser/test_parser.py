import pytest
from src.pdf_parser.parser import PDFParser

def test_parse_valid_pdf():
    parser = PDFParser()
    doc = parser.parse("./inputs/Алехин Максим P4219 Практика осень.pdf")
    assert doc.pages is not None
    # TODO: добавить проверки на наличие блоков