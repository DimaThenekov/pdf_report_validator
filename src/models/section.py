from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
from src.models.raw_document import TextBlock

if TYPE_CHECKING:
    from src.models.structured_document import StructuredDocument

@dataclass
class Section:
    title: str
    start_page: int
    end_page: int
    document: Optional['StructuredDocument'] = None  # строка

    def get_text_blocks(self) -> List[TextBlock]:
        """Возвращает блоки раздела, используя сохранённую ссылку на документ."""
        if self.document is None:
            return []
        return [
            b for b in self.document.raw_document.blocks
            if self.start_page <= b.page_num <= self.end_page
        ]