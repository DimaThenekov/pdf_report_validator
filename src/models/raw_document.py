from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class TextBlock:
    text: str
    font_name: str
    font_size: float
    bbox: tuple  # (x0, y0, x1, y1)
    page_num: int

@dataclass
class RawPDFDocument:
    """Сырые данные, извлечённые из PDF."""
    pages: List[int]
    blocks: List[TextBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)