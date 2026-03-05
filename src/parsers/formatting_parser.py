from typing import Dict, List, Any, Union, Optional

from src.models.raw_document import TextBlock
from src.models.section import Section
from src.models.structured_document import StructuredDocument
from .base_parser import BaseParser


class FormattingParser(BaseParser):
    """Парсер для проверки форматирования отчетов."""

    def __init__(self):
        # Коэффициент перевода миллиметров в пункты (1 мм = 72/25.4 pt)
        self.mm_to_pt = 72 / 25.4

    def _mm_to_pt(self, value_mm: float) -> float:
        return value_mm * self.mm_to_pt

    def parse(self, section_data: Union[StructuredDocument, Section], config: Dict[str, Any]) -> Dict[str, List]:
        result = {
            "errors": [],
            "warnings": [],
            "info": []
        }

        # 1. Преобразование размеров из мм в pt
        page_width_pt = None
        page_height_pt = None
        if "page_width_mm" in config and "page_height_mm" in config:
            page_width_pt = self._mm_to_pt(config["page_width_mm"])
            page_height_pt = self._mm_to_pt(config["page_height_mm"])

        margins_pt = {}
        if "margins_mm" in config:
            for k, v in config["margins_mm"].items():
                margins_pt[k] = self._mm_to_pt(v)

        # 2. Получение списка текстовых блоков
        blocks = self._extract_blocks(section_data)
        if not blocks:
            result["warnings"].append({"message": "Нет данных для проверки форматирования"})
            return result

        if (page_width_pt is None or page_height_pt is None) and isinstance(section_data, StructuredDocument):
            dims = section_data.get_page_dimensions(1)
            if dims:
                page_width_pt, page_height_pt = dims
        elif (page_width_pt is None or page_height_pt is None) and isinstance(section_data,
                                                                              Section) and section_data.document:
            dims = section_data.document.get_page_dimensions(1)
            if dims:
                page_width_pt, page_height_pt = dims

        # 3. Группировка блоков по страницам
        pages_dict = {}
        for block in blocks:
            pages_dict.setdefault(block.page_num, []).append(block)

        # 4. Основные требования из конфига
        required_font = config.get("font_name")
        font_size_range = config.get("font_size_range", (0, float('inf')))
        min_font_size, max_font_size = font_size_range

        check_page_numbers = config.get("check_page_numbers", False)
        first_page_has_number = config.get("first_page_has_number", False)
        page_number_position = config.get("page_number_position", "bottom_center")
        page_number_font_size_range = config.get("page_number_font_size_range", (0, float('inf')))

        # 5. Основной цикл по страницам
        for page_num, page_blocks in pages_dict.items():
            for block in page_blocks:
                # Пропускаем колонтитулы при проверке основного текста
                if page_height_pt and self._is_footer_or_header(block, page_height_pt):
                    continue

                # Проверка названия шрифта
                if required_font and block.font_name and required_font.lower() not in block.font_name.lower():
                    result["errors"].append({
                        "message": f"Шрифт '{block.font_name}' не соответствует требуемому '{required_font}'.",
                        "page": page_num,
                        "text_snippet": block.text[:50]
                    })

                # Проверка размера шрифта
                if block.font_size and (block.font_size < min_font_size or block.font_size > max_font_size):
                    result["errors"].append({
                        "message": f"Размер шрифта {block.font_size} пт вне допустимого диапазона ({min_font_size}-{max_font_size}).",
                        "page": page_num,
                        "text_snippet": block.text[:50]
                    })

                # Проверка полей (если есть координаты и размеры страницы)
                if page_width_pt and page_height_pt and margins_pt and block.bbox:
                    self._check_margins_for_block(block, page_num, page_width_pt, page_height_pt, margins_pt, result)

            # Проверка нумерации страниц (после обработки всех блоков страницы)
            if check_page_numbers:
                self._check_page_number_on_page(
                    page_num, page_blocks, page_height_pt, page_width_pt,
                    first_page_has_number, page_number_position, page_number_font_size_range, result
                )

        return result

    def _extract_blocks(self, section_data: Union[StructuredDocument, Section]) -> List[TextBlock]:
        """Извлекает текстовые блоки из переданных данных."""
        if isinstance(section_data, StructuredDocument):
            return section_data.raw_document.blocks
        elif isinstance(section_data, Section):
            # Предполагаем, что Section содержит ссылку на документ
            doc = getattr(section_data, 'document', None)
            if doc and isinstance(doc, StructuredDocument):
                return [
                    b for b in doc.raw_document.blocks
                    if section_data.start_page <= b.page_num <= section_data.end_page
                ]
        return []

    def _is_footer_or_header(self, block: TextBlock, page_height_pt: float) -> bool:
        """Определяет, находится ли блок в верхних 15% или нижних 15% страницы.
           В PDF координата y растёт снизу вверх: верх страницы – большие y."""
        if not block.bbox:
            return False
        y0, y1 = block.bbox[1], block.bbox[3]  # y0 - нижняя граница, y1 - верхняя
        # Верхние 15% страницы (header)
        if y0 > page_height_pt * 0.85:
            return True
        # Нижние 15% страницы (footer)
        if y1 < page_height_pt * 0.15:
            return True
        return False

    def _check_margins_for_block(self, block: TextBlock, page_num: int,
                                 page_width_pt: float, page_height_pt: float,
                                 margins_pt: Dict[str, float], result: Dict):
        """Проверяет, что блок не выходит за заданные поля с учётом допуска."""
        x0, y0, x1, y1 = block.bbox
        left_margin = margins_pt.get('left', 0)
        right_margin = margins_pt.get('right', 0)
        top_margin = margins_pt.get('top', 0)
        bottom_margin = margins_pt.get('bottom', 0)
        EPS = 1e-6  # допуск в пунктах

        if x0 < left_margin - EPS:
            result["errors"].append({
                "message": f"Текст выходит за левое поле (допустимо {left_margin:.1f} pt, фактически {x0:.1f} pt).",
                "page": page_num,
                "text_snippet": block.text[:30]
            })
        if x1 > page_width_pt - right_margin + EPS:
            result["errors"].append({
                "message": f"Текст выходит за правое поле (допустимо {right_margin:.1f} pt от края, фактически {page_width_pt - x1:.1f} pt).",
                "page": page_num,
                "text_snippet": block.text[:30]
            })
        if y1 > page_height_pt - top_margin + EPS:
            result["errors"].append({
                "message": f"Текст выходит за верхнее поле (допустимо {top_margin:.1f} pt, фактически {page_height_pt - y1:.1f} pt).",
                "page": page_num,
                "text_snippet": block.text[:30]
            })
        if y0 < bottom_margin - EPS:
            result["errors"].append({
                "message": f"Текст выходит за нижнее поле (допустимо {bottom_margin:.1f} pt, фактически {y0:.1f} pt).",
                "page": page_num,
                "text_snippet": block.text[:30]
            })

    def _check_page_number_on_page(self, page_num: int, page_blocks: List[TextBlock],
                                   page_height_pt: Optional[float], page_width_pt: Optional[float],
                                   first_page_has_number: bool, expected_position: str,
                                   font_size_range: tuple, result: Dict):
        """Проверяет наличие и корректность номера на странице."""
        if page_num == 1 and not first_page_has_number:
            return

        found = False
        for block in page_blocks:
            if page_height_pt and not self._is_footer_or_header(block, page_height_pt):
                continue
            text = block.text.strip()
            if text.isdigit() and int(text) == page_num:
                found = True
                # Проверка позиции
                if expected_position == "bottom_center" and block.bbox and page_width_pt:
                    x_center = (block.bbox[0] + block.bbox[2]) / 2
                    if abs(x_center - page_width_pt / 2) > page_width_pt * 0.1:  # допуск 10%
                        result["warnings"].append({
                            "message": f"Номер страницы {page_num} расположен не по центру нижнего поля.",
                            "page": page_num
                        })
                # Проверка размера шрифта
                if block.font_size:
                    if block.font_size < font_size_range[0] or block.font_size > font_size_range[1]:
                        result["warnings"].append({
                            "message": f"Размер шрифта номера страницы ({block.font_size} pt) вне диапазона {font_size_range}.",
                            "page": page_num
                        })
                break

        if not found:
            result["errors"].append({
                "message": f"Отсутствует номер страницы на странице {page_num}.",
                "page": page_num
            })