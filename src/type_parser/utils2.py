import re
from ..models.parsed_pdf import *

from typing import List

TOC_BLOCK_RE = re.compile(
    r""" ^
        \s*                     # начальные пробелы
        (?P<title>.+?)          # заголовок (ленивый)
        \s*                     # пробелы
        (?:[\.·•…]{3,}\s*)?     # опционально: точечки / лидеры
        (?P<page>\d{1,4})       # номер страницы
        \s*                     # хвостовые пробелы
        $
    """,
    re.VERBOSE,
)

TABLE_CAPTION_RE = re.compile(
    r"""^
    (?:Продолжение\s+)?        # опциональное 'Продолжение '
    Таблица                    # слово 'Таблица'
    \s*
    (?:№\s*)?                  # опциональное '№'
    \d+                        # номер
    \s*[–-]\s*                 # тире (– или -)
    .+                         # остальной текст
    $""",
    re.IGNORECASE | re.VERBOSE,
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
    (?:Продолжение\s+)?        # опциональное 'Продолжение '
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
        text=span.get("text", ""),
        bbox=Bbox(x0, y0, x1, y1),
        style=style,
    )


def split_block_into_lineblock(block: dict, gap_tol: float = 10.0) -> LineBlock:
    lines = block.get("lines", [])
    if not lines:
        return LineBlock(text_blocks=[], bbox=Bbox(0, 0, 0, 0))

    text_blocks: List[TextBlock] = []
    for line in lines:
        for span in line.get("spans", []):
            tb = make_textblock_from_span(span)
            if tb.text:
                text_blocks.append(tb)

    if not text_blocks:
        return LineBlock(text_blocks=[], bbox=Bbox(0, 0, 0, 0))

    text_blocks.sort(key=lambda tb: tb.bbox.x0)

    columns: List[List[TextBlock]] = []
    current_col: List[TextBlock] = [text_blocks[0]]

    for prev, cur in zip(text_blocks, text_blocks[1:]):
        gap = cur.bbox.x0 - prev.bbox.x1
        if gap > gap_tol:
            columns.append(current_col)
            current_col = [cur]
        else:
            current_col.append(cur)
    columns.append(current_col)

    merged_text_blocks: List[TextBlock] = []
    for col in columns:
        col_text = "".join(tb.text for tb in col)

        style_weights = defaultdict(int)
        for tb in col:
            if tb.text and tb.style:
                style_weights[tb.style] += len(tb.text)
        main_style = max(style_weights.items(), key=lambda kv: kv[1])[0] 

        x0 = min(tb.bbox.x0 for tb in col)
        y0 = min(tb.bbox.y0 for tb in col)
        x1 = max(tb.bbox.x1 for tb in col)
        y1 = max(tb.bbox.y1 for tb in col)
        merged_text_blocks.append(TextBlock(col_text, Bbox(x0, y0, x1, y1), main_style))

    x0 = min(tb.bbox.x0 for tb in merged_text_blocks)
    y0 = min(tb.bbox.y0 for tb in merged_text_blocks)
    x1 = max(tb.bbox.x1 for tb in merged_text_blocks)
    y1 = max(tb.bbox.y1 for tb in merged_text_blocks)

    return LineBlock(text_blocks=merged_text_blocks, bbox=Bbox(x0, y0, x1, y1))


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

def get_raw_block_type(block: dict) -> RawBlockType:
    if block.get("image"):
        return RawBlockType.FIGURE
    line_block = split_block_into_lineblock(block)
    if (len(line_block.text_blocks) == 0):
        return RawBlockType.UNUSED
    if (len(line_block.text_blocks) > 1):
        return RawBlockType.TABLE
    block_text = line_block.text_blocks[0].text
    if TOC_CAPTION_RE.match(block_text.strip()):
        return RawBlockType.TOC_CAPTION
    if PAGE_NUMBER_RE.match(block_text.strip()):
        return RawBlockType.UNUSED
    if TABLE_CAPTION_RE.match(block_text.strip()):
        return RawBlockType.TABLE_CAPTION
    if FIGURE_CAPTION_RE.match(block_text.strip()):
        return RawBlockType.FIGURE_CAPTION
    return RawBlockType.TEXT
    
def get_table_caption(paragraph: ParagraphBlock) -> Caption:
    pass

def get_figure_caption(paragraph: ParagraphBlock) -> Caption:
    pass