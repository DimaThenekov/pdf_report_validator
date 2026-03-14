import re
from ..models.structured_document import *

TOC_BLOCK_RE = re.compile(
    r""" ^
        \s*                               # начальные пробелы
        (?P<title>.+?)                    # заголовок (ленивый)
        \s*                               # пробелы перед точками
        (?:(?:[\.·•…]\s*){3,})?           # опционально: минимум 3 символа-точки, 
                                          # между которыми могут быть пробелы
        (?P<page>\d{1,4})                 # номер страницы
        \s*                               # хвостовые пробелы
        $
    """,
    re.VERBOSE,
)


TABLE_CAPTION_RE = re.compile(
    r"""^
    Таблица                    # слово 'Таблица'
    \s*
    (?:№\s*)?                  # опциональное '№'
    \d+                        # номер
    \s*[–-]\s*                 # тире (– или -)
    .+                         # остальной текст
    $""",
    re.IGNORECASE | re.VERBOSE,
)

TABLE_CONTINUATION_RE = re.compile(
    r"""
    ^                           # Начало строки
    Продолжение\s+таблицы\s+№   # Фиксированный текст с любыми пробелами
    \s*                         # Возможный пробел после знака №
    \d+                         # Номер таблицы (одна или более цифр)
    .*                          # Любые символы до конца (тире, название и т.д.)
    $                           # Конец строки
    """,
    re.IGNORECASE | re.VERBOSE
)


TOC_CAPTION_RE = re.compile(
    r"""(?<!\S)        # слева не буква/цифра (начало или пробел/знак)
    (Содержание|Оглавление)
    (?!\S)             # справа не буква/цифра
    """,
    re.IGNORECASE | re.VERBOSE,
)

FIGURE_CAPTION_RE = re.compile(
    r"""^
    (?:Рисунок|Скриншот)       # Рисунок или Скриншот
    \s*
    (?:№\s*)?                  # опциональное '№'
    \d+                        # номер
    \s*[–-]\s*                 # тире (– или -)
    .+                         # остальной текст
    $""",
    re.IGNORECASE | re.VERBOSE,
)

PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")

def make_textblock_from_span(span: dict) -> TextBlock:
    x0, y0, x1, y1 = span["bbox"]
    style = Style(
        font=span.get("font", ""),
        size=span.get("size", 0.0),
        color=span.get("color", 0),
    )
    return TextBlock(
        text=span.get("text", "").strip(),
        bbox=Bbox(x0, y0, x1, y1),
        style=style,
    )


from collections import defaultdict

def split_block_into_lineblock(block: dict) -> LineBlock:
    lines = block.get("lines", [])
    all_line_tbs = []

    for line in lines:
        spans = line.get("spans", [])
        line_tbs = [make_textblock_from_span(s) for s in spans if make_textblock_from_span(s).text]
        
        if not line_tbs:
            continue
            
        line_tbs.sort(key=lambda tb: tb.bbox.x0)
        text = " ".join(tb.text.strip() for tb in line_tbs)
        
        style_weights = defaultdict(int)
        for tb in line_tbs:
            style_weights[tb.style] += len(tb.text)
        main_style = max(style_weights.items(), key=lambda kv: kv[1])[0]

        lx0 = min(tb.bbox.x0 for tb in line_tbs)
        ly0 = min(tb.bbox.y0 for tb in line_tbs)
        lx1 = max(tb.bbox.x1 for tb in line_tbs)
        ly1 = max(tb.bbox.y1 for tb in line_tbs)
        
        all_line_tbs.append(TextBlock(text, Bbox(lx0, ly0, lx1, ly1), main_style))

    if not all_line_tbs:
        return LineBlock(text_blocks=[], bbox=Bbox(0, 0, 0, 0))

    gx0 = min(tb.bbox.x0 for tb in all_line_tbs)
    gy0 = min(tb.bbox.y0 for tb in all_line_tbs)
    gx1 = max(tb.bbox.x1 for tb in all_line_tbs)
    gy1 = max(tb.bbox.y1 for tb in all_line_tbs)

    return LineBlock(text_blocks=all_line_tbs, bbox=Bbox(gx0, gy0, gx1, gy1))


class RawBlockType(Enum):
    UNUSED = 1
    TABLE = 2
    TOC_CAPTION = 3
    TABLE_CAPTION = 4
    FIGURE_CAPTION = 5
    FIGURE = 6
    TEXT = 7

def is_heading_candidate(paragraph: ParagraphBlock, toc: TocBlock):
    text = paragraph.text
    if toc:
        if toc.entries.get(text.lower()):
            return True
        else:
            return False
    else:
        return False
    
def is_in_table(top: float, bottom: float, table: TableInfo):
    return table.horizontal_lines[0] <= (top + bottom) / 2 and table.horizontal_lines[-1] >= (top + bottom) / 2
    
def get_table_caption(paragraph: ParagraphBlock) -> Caption:
    pass

def get_figure_caption(paragraph: ParagraphBlock) -> Caption:
    pass

def intersection(text_block: TextBlock, column_info: ColumnInfo) -> bool:
    return text_block.bbox.x0 >= column_info.left_border and text_block.bbox.x1 <= column_info.right_border

def expand_line_to_table(line_block: LineBlock, table: TableInfo) -> LineBlock:
    columns = []
    bbox = line_block.bbox
    for column in table.columns:
        result = TextBlock(
            "",
            Bbox(
                column.left_border,
                bbox.y0,
                column.right_border,
                bbox.y1
            ),
            None
        )
        for text_block in line_block.text_blocks:
            if (intersection(text_block, column)):
                result = text_block
                break
        columns.append(result)
    return LineBlock(
        columns,
        Bbox(
            min(tb.bbox.x0 for tb in columns),
            bbox.y0,
            max(tb.bbox.x1 for tb in columns),
            bbox.y1
        )
    )

def has_between(a: list[float], left: float, right: float) -> bool:
    from bisect import bisect_left
    i = bisect_left(a, left)
    return i < len(a) and a[i] <= right

def is_table_continuation(paragraph: ParagraphBlock) -> bool:
    return TABLE_CONTINUATION_RE.match(paragraph.text)
