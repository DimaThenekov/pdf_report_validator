from typing import Dict, List, Any, Union
from src.models.structured_document import TextBlock
from src.models.section import Section
from src.models.message import MessageCollector
from .base_parser import BaseParser


class FormattingParser(BaseParser):
    """Парсер для проверки форматирования отчетов с использованием новых моделей TextBlock и Style."""

    def __init__(self):
        # Коэффициент перевода миллиметров в пункты (1 мм = 72/25.4 pt)
        self.mm_to_pt = 72 / 25.4

    def _mm_to_pt(self, value_mm: float) -> float:
        return value_mm * self.mm_to_pt

    def parse(self, data: Union[Section, List[TextBlock]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        collector = MessageCollector()

        # 1. Преобразование размеров страницы из мм в pt
        page_width_pt = self._mm_to_pt(config.get("page_width_mm", 210))
        page_height_pt = self._mm_to_pt(config.get("page_height_mm", 297))

        margins_pt = {}
        if "margins_mm" in config:
            margins_pt = {k: self._mm_to_pt(v) for k, v in config["margins_mm"].items()}

        # 2. Получение списка текстовых блоков
        blocks = data.get_text_blocks() if isinstance(data, Section) else data

        if not blocks:
            collector.add_warning(0, "Нет данных для проверки форматирования")
            return collector.to_list()

        # 3. Группировка блоков по страницам
        pages_dict = {}
        for block in blocks:
            # Предполагаем наличие атрибута page_num, в противном случае используем дефолтную страницу 1
            page_num = getattr(block, 'page_num', getattr(block, 'page', 1))
            pages_dict.setdefault(page_num, []).append(block)

        # 4. Основные требования из конфига
        required_font = config.get("font_name")
        font_size_range = config.get("font_size_range", (0, float('inf')))

        # 5. Основной цикл по страницам
        for page_num, page_blocks in pages_dict.items():
            for block in page_blocks:
                # Генерируем ID для блока, если его нет (для MessageCollector)
                block_id = getattr(block, 'id', hash(block.text) % 100000 if hasattr(block, 'text') else 0)

                # Пропускаем колонтитулы при проверке основного текста
                if self._is_footer_or_header(block, page_height_pt):
                    continue

                # Проверка названия шрифта
                if required_font and block.style and block.style.font:
                    if required_font.lower() not in block.style.font.lower():
                        collector.add_error(block_id,
                                            f"Шрифт '{block.style.font}' не соответствует требуемому '{required_font}'.")

                # Проверка размера шрифта
                if block.style and block.style.size:
                    if not (font_size_range[0] <= block.style.size <= font_size_range[1]):
                        collector.add_error(block_id,
                                            f"Размер шрифта {block.style.size} пт вне допустимого диапазона ({font_size_range[0]}-{font_size_range[1]}).")

                # Проверка полей
                if margins_pt and block.bbox:
                    self._check_margins(block, page_num, page_width_pt, page_height_pt, margins_pt, collector)

            # Проверка нумерации страниц (после обработки всех блоков)
            if config.get("check_page_numbers"):
                self._check_page_number_on_page(page_num, page_blocks, page_height_pt, page_width_pt, config, collector)

        return collector.to_list()

    def _is_footer_or_header(self, block: TextBlock, page_height_pt: float) -> bool:
        """Определяет, находится ли блок в верхних 15% или нижних 15% страницы."""
        if not block.bbox:
            return False
        y0, y1 = block.bbox.y0, block.bbox.y1
        # Верхние 15% страницы (header)
        if y0 > page_height_pt * 0.85:
            return True
        # Нижние 15% страницы (footer)
        if y1 < page_height_pt * 0.15:
            return True
        return False

    def _check_margins(self, block: TextBlock, page_num: int,
                       width: float, height: float, margins: dict,
                       collector: MessageCollector):
        """Проверяет, что блок не выходит за заданные поля с учётом допуска."""
        b = block.bbox
        block_id = getattr(block, 'id', hash(block.text) % 100000 if hasattr(block, 'text') else 0)
        eps = 1e-6  # допуск

        if b.x0 < margins.get('left', 0) - eps:
            collector.add_error(block_id,
                                f"Текст выходит за левое поле (допустимо {margins.get('left', 0):.1f} pt, фактически {b.x0:.1f} pt).")
        if b.x1 > width - margins.get('right', 0) + eps:
            collector.add_error(block_id, f"Текст выходит за правое поле (фактически отступ {width - b.x1:.1f} pt).")
        if b.y1 > height - margins.get('top', 0) + eps:
            collector.add_error(block_id, f"Текст выходит за верхнее поле.")
        if b.y0 < margins.get('bottom', 0) - eps:
            collector.add_error(block_id, f"Текст выходит за нижнее поле.")

    def _check_page_number_on_page(self, page_num: int, page_blocks: List[TextBlock],
                                   page_height_pt: float, page_width_pt: float,
                                   config: dict, collector: MessageCollector):
        """Проверяет наличие и корректность номера на странице."""
        first_page_has_number = config.get("first_page_has_number", False)
        expected_position = config.get("page_number_position", "bottom_center")
        font_size_range = config.get("page_number_font_size_range", (0, float('inf')))

        if page_num == 1 and not first_page_has_number:
            return

        found = False
        for block in page_blocks:
            if page_height_pt and not self._is_footer_or_header(block, page_height_pt):
                continue

            text = block.text.strip()
            if text.isdigit() and int(text) == page_num:
                found = True
                block_id = getattr(block, 'id', hash(block.text) % 100000)

                # Проверка позиции
                if expected_position == "bottom_center" and block.bbox and page_width_pt:
                    x_center = (block.bbox.x0 + block.bbox.x1) / 2
                    if abs(x_center - page_width_pt / 2) > page_width_pt * 0.1:  # допуск 10%
                        collector.add_warning(block_id,
                                              f"Номер страницы {page_num} расположен не по центру нижнего поля.")

                # Проверка размера шрифта
                if block.style and block.style.size:
                    if not (font_size_range[0] <= block.style.size <= font_size_range[1]):
                        collector.add_warning(block_id,
                                              f"Размер шрифта номера страницы ({block.style.size} pt) вне диапазона {font_size_range}.")
                break

        if not found:
            collector.add_error(0, f"Отсутствует номер страницы на странице {page_num}.")