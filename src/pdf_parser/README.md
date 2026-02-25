# Модуль `pdf_parser`

**Ответственный**: Ярослав Левченко (P3418)

Модуль отвечает за первичное извлечение данных из PDF-файла.  
Он использует библиотеку [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) для получения текста, информации о шрифтах, координат текстовых блоков и метаданных документа.

Выходные данные представляются в виде объекта `RawPDFDocument` (модель из `src.models.raw_document`), который затем передаётся в модуль `type_parser` для дальнейшей структуризации.

## Основные возможности

- Извлечение текста с сохранением позиционирования (координаты блока).
- Получение имени и размера шрифта для каждого текстового фрагмента.
- Сбор информации о страницах (количество, размеры).

## Установка зависимостей

Модуль требует установки PyMuPDF. Зависимости проекта описаны в корневом `requirements.txt`:

```txt
PyMuPDF>=1.23.0
```

Рекомендуется использовать виртуальное окружение.

## Использование

### Класс `PDFParser`

Основной интерфейс модуля — класс `PDFParser` из `src.pdf_parser.parser`.

```python
from src.pdf_parser.parser import PDFParser

parser = PDFParser()
raw_doc = parser.parse("path/to/document.pdf")
```

### Входные параметры

- `pdf_path` (str): путь к PDF-файлу.

### Возвращаемое значение

Объект `RawPDFDocument`, определённый в `src.models.raw_document`:

```python
@dataclass
class TextBlock:
    text: str
    font_name: str
    font_size: float
    bbox: tuple      # (x0, y0, x1, y1) в пунктах
    page_num: int

@dataclass
class RawPDFDocument:
    pages: List[int]
    blocks: List[TextBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

- `pages` — список номеров страниц (обычно просто индексы от 0 до N-1).
- `blocks` — все текстовые блоки, извлечённые со всех страниц.
- `metadata` — словарь с метаданными PDF (например, `author`, `title`, `producer`).

### Пример

```python
from src.pdf_parser.parser import PDFParser

parser = PDFParser()
doc = parser.parse("examples/sample_bachelor.pdf")

print(f"Страниц: {len(doc.pages)}")
print(f"Найдено блоков: {len(doc.blocks)}")
if doc.blocks:
    first = doc.blocks[0]
    print(f"Первый блок: '{first.text[:50]}...' шрифт {first.font_name} {first.font_size}pt")
```

## Тестирование

Для модуля подготовлены тесты в директории `tests/test_pdf_parser/`.

Запустить только тесты `pdf_parser` можно командой из корня проекта:

```bash
pytest tests/test_pdf_parser/ -v
```

При написании тестов используйте примеры PDF-файлов из папки `examples/`.  
Для изолированного тестирования можно создать синтетические PDF с помощью `PyMuPDF` или других библиотек.

## Разработка и доработка

В текущей версии модуль содержит заглушки. Необходимо реализовать:

- Извлечение блоков текста с помощью `page.get_text("dict")`.
- Сохранение информации о шрифте и координатах.
- Заполнение метаданных из `doc.metadata`.

См. комментарии `# TODO` в файлах `src/pdf_parser/parser.py` и `src/pdf_parser/utils.py`.

### Рекомендации по реализации

- Используйте `fitz.TEXT_PRESERVE_IMAGES | fitz.TEXT_PRESERVE_LIGATURES` при необходимости.
- Для получения шрифтов извлекайте их из словаря, возвращаемого `get_text("dict")`.
- Координаты в PyMuDF измеряются в пунктах (1/72 дюйма). При необходимости преобразования в сантиметры учитывайте это позже (в других модулях).

## Связь с другими модулями

Выходные данные `RawPDFDocument` потребляются модулем `type_parser`. Поэтому важно сохранять максимум информации, особенно:

- имена шрифтов (оригинальные, как в PDF);
- размеры шрифтов;
- координаты блоков для последующего анализа отступов и полей.

## Дополнительная информация

- [Документация PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)
- [Общее описание проекта PDF Report Validator](../../README.md)