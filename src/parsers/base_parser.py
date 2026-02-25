from abc import ABC, abstractmethod
from src.models.structured_document import StructuredDocument

class BaseParser(ABC):
    """Базовый класс для всех парсеров разделов."""
    
    @abstractmethod
    def parse(self, section_data, config: dict) -> dict:
        """
        Принимает данные раздела (текст, метаданные) и возвращает результаты проверки.
        Результат – словарь с найденными нарушениями/замечаниями.
        """
        pass

# Пример конкретного парсера
class TitlePageParser(BaseParser):
    def parse(self, section_data, config):
        # TODO: проверить наличие всех полей на титульном листе
        return {"errors": [], "warnings": []}