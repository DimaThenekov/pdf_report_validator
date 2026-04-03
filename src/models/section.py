from dataclasses import dataclass, field
from typing import List
from src.models.structured_document import TextBlock

@dataclass
class Section:
    title: str
    start_page: int
    end_page: int
    blocks: List[TextBlock] = field(default_factory=list)

    def get_text_blocks(self) -> List[TextBlock]:
        """Возвращает блоки раздела."""
        return self.blocks