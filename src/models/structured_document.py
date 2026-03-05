from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from src.models.raw_document import RawPDFDocument, TextBlock
from src.models.section import Section  # прямой импорт допустим

@dataclass
class StructuredDocument:
    raw_document: RawPDFDocument
    sections: List[Section] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Устанавливаем обратную ссылку для каждого раздела
        for section in self.sections:
            section.document = self

    def get_page_blocks(self, page_num: int) -> List['TextBlock']:
        return [b for b in self.raw_document.blocks if b.page_num == page_num]

    def get_page_dimensions(self, page_num: int) -> Optional[Tuple[float, float]]:
        dims = self.raw_document.metadata.get('page_dimensions')
        if dims and 0 <= page_num - 1 < len(dims):
            return dims[page_num - 1]
        return None