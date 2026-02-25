from src.models.structured_document import StructuredDocument
from typing import List, Tuple

class ParsersMatcher:
    """Определяет, какие парсеры (из модуля parsers) нужно применить к разделам."""
    
    def match(self, doc: StructuredDocument) -> List[Tuple[str, str]]:
        """
        Возвращает список пар (название раздела, имя парсера).
        Например: [("title_page", "TitlePageParser"), ("introduction", "IntroductionParser")]
        """
        # TODO: реализовать на основе конфигурации и заголовков
        return []