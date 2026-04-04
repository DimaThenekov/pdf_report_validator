'''
import pytest
from src.models.structured_document import TextBlock, Bbox, Style
from src.parsers.formatting_parser import FormattingParser


@pytest.fixture
def sample_blocks():
    """Создает тестовые блоки с новыми объектами Bbox и Style."""
    blocks = [
        # Страница 1: Основной текст (ID=1)
        TextBlock(
            text="Введение в научную работу",
            style=Style(font="TimesNewRoman", size=14.0, color=0),
            bbox=Bbox(x0=86.0, y0=700.0, x1=400.0, y1=720.0)
        ),
        # Страница 1: Ошибка шрифта (ID=2)
        TextBlock(
            text="Этот текст набран неправильным шрифтом",
            style=Style(font="Arial", size=14.0, color=0),
            bbox=Bbox(x0=86.0, y0=600.0, x1=400.0, y1=620.0)
        ),
        # Страница 1: Блок в верхнем колонтитуле (ID=3) - Arial не должен выдать ошибку
        TextBlock(
            text="МИНИСТЕРСТВО НАУКИ",
            style=Style(font="Arial", size=10.0, color=0),
            bbox=Bbox(x0=86.0, y0=800.0, x1=400.0, y1=820.0)
        ),
        # Страница 2: Выход за левое поле (ID=4)
        TextBlock(
            text="Текст, который выходит за левое поле",
            style=Style(font="TimesNewRoman", size=12.0, color=0),
            bbox=Bbox(x0=10.0, y0=500.0, x1=400.0, y1=520.0)  # 10 pt < левого поля 85 pt
        ),
        # Страница 2: Блок с номером страницы, смещенный влево (ID=5)
        TextBlock(
            text="2",
            style=Style(font="TimesNewRoman", size=11.0, color=0),
            bbox=Bbox(x0=50.0, y0=50.0, x1=60.0, y1=65.0)  # Смещен от центра
        ),
    ]

    # Имитируем наличие page_num и id, так как парсер их ожидает
    for i, b in enumerate(blocks):
        b.id = i + 1
        b.page_num = 1 if i < 3 else 2

    return blocks


class TestFormattingParser:

    def test_parser_returns_list_of_dicts(self, sample_blocks):
        """Проверка, что парсер возвращает правильный формат (MessageCollector.to_list())."""
        parser = FormattingParser()
        config = {
            "font_name": "TimesNewRoman",
            "page_width_mm": 210,
            "page_height_mm": 297
        }

        results = parser.parse(sample_blocks, config)
        assert isinstance(results, list)
        if len(results) > 0:
            assert "type" in results[0]
            assert "blockId" in results[0]
            assert "text" in results[0]

    def test_font_error_detection(self, sample_blocks):
        """Обнаружение неправильного шрифта (Arial вместо TimesNewRoman)."""
        parser = FormattingParser()
        config = {
            "font_name": "TimesNewRoman",
            "font_size_range": (12, 14),
            "page_width_mm": 210,
            "page_height_mm": 297,
            "check_page_numbers": False
        }

        results = parser.parse(sample_blocks, config)
        errors = [r for r in results if r["type"] == "errors"]

        # Блок ID 2 имеет шрифт Arial
        font_errors = [e for e in errors if "Arial" in e["text"]]
        assert len(font_errors) == 1
        assert font_errors[0]["blockId"] == 2

    def test_footer_exclusion(self, sample_blocks):
        """Проверка, что блоки в колонтитулах не проверяются на основной шрифт."""
        parser = FormattingParser()
        config = {
            "font_name": "TimesNewRoman",
            "page_height_mm": 297,
            "check_page_numbers": False
        }

        results = parser.parse(sample_blocks, config)
        errors = [r for r in results if r["type"] == "errors"]

        # Блок ID 3 (колонтитул) имеет Arial, но он не должен выдать ошибку
        assert not any(e["blockId"] == 3 and "Arial" in e["text"] for e in errors)

    def test_margins_error(self, sample_blocks):
        """Проверка выхода текста за поля."""
        parser = FormattingParser()
        config = {
            "font_name": "TimesNewRoman",
            "margins_mm": {"top": 20, "bottom": 20, "left": 30, "right": 15},  # Левое поле 30мм ~ 85pt
            "page_width_mm": 210,
            "page_height_mm": 297,
            "check_page_numbers": False
        }

        results = parser.parse(sample_blocks, config)
        errors = [r for r in results if r["type"] == "errors"]

        # Блок ID 4 имеет x0=10.0, что меньше 85pt
        margin_errors = [e for e in errors if "левое поле" in e["text"]]
        assert len(margin_errors) >= 1
        assert any(e["blockId"] == 4 for e in margin_errors)

    def test_page_number_position_warning(self, sample_blocks):
        """Номер страницы расположен не по центру."""
        parser = FormattingParser()
        config = {
            "check_page_numbers": True,
            "first_page_has_number": False,
            "page_number_position": "bottom_center",
            "page_number_font_size_range": (10, 12),
            "page_width_mm": 210,
            "page_height_mm": 297
        }

        results = parser.parse(sample_blocks, config)
        warnings = [r for r in results if r["type"] == "warnings"]

        # Блок ID 5 - это номер страницы 2, смещенный влево (x0=50)
        pos_warnings = [w for w in warnings if "не по центру" in w["text"]]
        assert len(pos_warnings) >= 1
        assert any(w["blockId"] == 5 for w in pos_warnings)
