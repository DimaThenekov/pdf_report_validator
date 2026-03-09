from collections import defaultdict
import re
from typing import Any, Counter, Dict, Tuple

from src.models.structured_document import BlockContent, BlockInfo, BlockStyle, ColumnContent, ColumnInfo, DocumentStyle, StyleDescription, TableMetainfo, TocEntry

SPACE_RE = re.compile(r"\s+")
TOC_TITLE_WORDS = ("содержание", "оглавление")
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
PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")
TABLE_CAPTION_RE = re.compile(
    r"""
    ^\s*
    (?:Продолжение\s+)?   # опционально: 'Продолжение '
    таблицы?              # 'таблица' / 'таблицы'
    \s*
    (?:№\s*)?             # опционально: '№'
    (?P<num>\d+(?:\.\d+)*)# номер: 1, 1.2, 1.2.3 ...
    \s*[-–:]?\s*          # опциональное тире/двоеточие с пробелами
    (?P<title>.*)         # произвольная подпись (может быть пустой)
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

PICTURE_CAPTION_RE = re.compile(
    r""
)

def inc(page_idx, block_idx, pages):
    if block_idx + 1 == len(pages[page_idx].get("blocks", [])):
        return page_idx + 1, 0
    else:
        return page_idx, block_idx + 1


def is_toc_title_block(block: dict) -> bool:
    text = get_block_single_line_text(block)
    return any(w in text.lower() for w in TOC_TITLE_WORDS)


#Проверено
def get_block_font_stats(block: dict) -> StyleDescription:
    sizes = Counter()
    fonts = Counter()
    colors = Counter()
    left_indents = Counter()
    right_indents = Counter()

    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if not SPACE_RE.sub("", span.get("text", "")):
                continue

            s, f, c = span.get("size"), span.get("font"), span.get("color")

            if s:
                sizes[round(s, 1)] += 1
            if f:
                fonts[f] += 1
            if c is not None:
                colors[c] += 1
    
    left_indents[block["bbox"][0]] += 1
    right_indents[block["bbox"][2]] += 1

    return StyleDescription(
        fonts=fonts,
        sizes=sizes,
        colors=colors,
        left_indents=left_indents,
        right_indents=right_indents
    )


#Проверено
#Определяем основной стиль блока текста
def get_block_main_style(block: dict) -> BlockStyle:
    style = get_block_font_stats(block)
    size = style.sizes.most_common(1)[0][0] if style.sizes else None
    font = style.fonts.most_common(1)[0][0] if style.fonts else None
    color = style.colors.most_common(1)[0][0] if style.colors else None
    indent_left = style.left_indents.most_common(1)[0][0]
    indent_right = style.right_indents.most_common(1)[0][0]
    return BlockStyle(
        main_font=font,
        main_size=size,
        main_color=color,
        indent_left=indent_left,
        indent_right=indent_right
    )


#Проверено
#Подсчитываем наиболее часто встречающийся в документе шрифт, размер, цвет, а также 
#минимальный и максимальный отступы слева и справа
def compute_body_main_style(pages_dicts: list[dict]) -> DocumentStyle:
    acc_style = StyleDescription()
    for page in pages_dicts:
        for block in page.get("blocks", []):
            styles = get_block_font_stats(block)
            acc_style += styles
    return DocumentStyle(acc_style)


# Проверено
# Получаем весь текст блока одной строкой
def get_block_single_line_text(block: dict) -> str:
    parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            parts.append(span.get("text", ""))
    raw = "".join(parts)
    text = re.sub(r"\s+", " ", raw).strip()
    return text


# Получаем весь текст одной line
def get_line_text(line: dict) -> str:
    parts = []
    for span in line.get("spans", []):
        parts.append(span.get("text", ""))
    raw = "".join(parts)
    return SPACE_RE.sub(" ", raw).strip()


# Разбиваем блок на логические колонки
def build_block_content(
    block: dict,
    min_gap: float = 40.0,
) -> BlockContent:
    lines = block.get("lines", [])
    if not lines:
        return BlockContent(
            columns=[],
            left_indent=0.0,
            right_indent=0.0,
            top_indent=0.0,
            bottom_indent=0.0,
        )

    # группируем строки в колонки
    lines_sorted = sorted(lines, key=lambda l: l["bbox"][0])
    column_boxes: list[dict] = []

    for line in lines_sorted:
        lx0, ly0, lx1, ly1 = line["bbox"]
        text = get_line_text(line)
        if not text:
            continue

        if not column_boxes or (lx0 - column_boxes[-1]["bbox"][2]) > min_gap:
            column_boxes.append({
                "bbox": [lx0, ly0, lx1, ly1],
                "text": text,
            })
        else:
            last = column_boxes[-1]
            last["text"] = f"{last['text']} {text}".strip()
            last["bbox"][0] = min(last["bbox"][0], lx0)
            last["bbox"][1] = min(last["bbox"][1], ly0)
            last["bbox"][2] = max(last["bbox"][2], lx1)
            last["bbox"][3] = max(last["bbox"][3], ly1)

    columns = [
        ColumnContent(
            text=col["text"],
            start_indent=col["bbox"][0],
            end_indent=col["bbox"][2],
        )
        for col in column_boxes
    ]

    if columns:
        left_indent = min(c.start_indent for c in columns)
        right_indent = max(c.end_indent for c in columns)
    else:
        left_indent = 0.0
        right_indent = 0.0

    bx0, by0, bx1, by1 = block["bbox"]
    top_indent = by0
    bottom_indent = by1

    return BlockContent(
        columns=columns,
        left_indent=left_indent,
        right_indent=right_indent,
        top_indent=top_indent,
        bottom_indent=bottom_indent,
    )


# Проверено 
# Определяем, является ли данный блок блоком содержания
def is_toc_entry_block(block: dict) -> bool:
    text = get_block_single_line_text(block)
    if not text:
        return False
    return TOC_BLOCK_RE.match(text) is not None


# Проверено
# Парсим строку содержания в нужный нам вид (Название - страница)
def parse_toc_entry_block(block: dict) -> TocEntry | None:
    text = get_block_single_line_text(block)
    if not text:
        return None
    m = TOC_BLOCK_RE.match(text)
    if not m:
        return None
    title = m.group("title").strip()
    page = int(m.group("page"))
    return TocEntry(
        title=title,
        target_page=page,
        raw_line=text
    )


def get_heading_style(block: dict) -> HeadingStyle:

    style = get_block_font_stats(block)
    font = style["font"]
    size = style["size"]
    color = style["color"]

    if block.get("lines"):
        x0 = block["lines"][0]["bbox"][0]
    else:
        x0 = block["bbox"][0]

    return HeadingStyle(
        font_name=font,
        font_size=size,
        color=color,
        indent_x=x0
    )

def check_heading_style(style: BlockStyle, styles: list[BlockStyle]): 
    for i in range(len(styles)):
        if style.main_size == styles[i].main_size:
            return i
    return -1


def is_heading_candidate(block: dict, toc: BlockInfo, main_style: dict):
    text = get_block_single_line_text(block)
    if not text.strip():
        return False
    
    if not toc:
        style = get_heading_style(block)
        if style.font_size > main_style["size"] and len(text) < 200:
            return True

    if toc and toc.metainfo.entries.get(text.strip().lower()):
        return True
    
    return False

def is_paragraph_start(block: dict, main_style: DocumentStyle):
    text = get_block_single_line_text(block)
    if not text.strip():
        return False
    
    style = get_block_main_style(block)
    indent_left = style.indent_left
    if indent_left > main_style.min_indent_left:
        return True
    return False


def continues_paragraph(block: dict, main_style: DocumentStyle):
    style = get_block_main_style(block)
    indent_left = style.indent_left
    if (indent_left == main_style.min_indent_left):
        return True
    return False

def is_table_start(block: dict) -> bool:
    block_content = build_block_content(block)
    columns = block_content.columns
    if (len(columns) > 1):
        return True
    return False

def parse_table_start(table) -> TableMetainfo:
    row = table.rows[0]
    cell_boxes = row.cells
    cell_texts = table.extract()[0]
    column_info = [
        ColumnInfo(
            cell_texts[i],
            cell_boxes[i][0],
            cell_boxes[i][2]
        ) for i in range(len(cell_texts))
    ]
    return TableMetainfo(
        len(cell_texts),
        column_info,
        [],
        table.bbox[0],
        table.bbox[2]
    )


#def parse_table_start(block: dict) -> TableMetainfo | None:
    block_content = build_block_content(block)
    columns = block_content.columns

    if (len(columns) > 1):
        return TableMetainfo(
            columns_count=len(columns),
            column_names=block_content,
            rows = [],
            indent_left=block_content.left_indent,
            indent_right=block_content.right_indent
        )
    return None

def is_page_number_block(block: dict):
    text = get_block_single_line_text(block).strip()
    if not text:
        return False
    parts = text.split()
    if len(parts) != 1:
        return False
    return PAGE_NUMBER_RE.match(text) is not None

def is_table_caption_block(block: dict) -> bool:
    text = get_block_single_line_text(block)
    if not text.strip():
        return False
    return TABLE_CAPTION_RE.match(text) is not None

def is_empty_block(block: dict) -> bool:
    text = get_block_single_line_text(block)
    if text.strip():
        return False
    return True


def _interval_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def align_block_to_columns(
    block: BlockContent,
    columns_info: list[ColumnInfo],
    overlap_ratio_threshold: float = 0.3,
) -> BlockContent:
    """
    Для каждой колонки из columns_info ищет подходящую колонку block.columns
    по X-пересечению. Если подходящей нет — ставит пустую ColumnContent
    с теми же границами.
    overlap_ratio_threshold — минимальная доля пересечения по ширине
    обоих интервалов (берётся минимум из двух долей).
    """
    aligned_cols: list[ColumnContent] = []

    for info in columns_info:
        t0, t1 = info.left_indent, info.right_indent
        best_col: ColumnContent | None = None
        best_score = 0.0

        for col in block.columns:
            c0, c1 = col.start_indent, col.end_indent
            overlap = _interval_overlap(t0, t1, c0, c1)
            if overlap <= 0:
                continue

            t_len = t1 - t0
            c_len = c1 - c0
            if t_len <= 0 or c_len <= 0:
                continue

            r_t = overlap / t_len
            r_c = overlap / c_len
            score = min(r_t, r_c)
            if score >= overlap_ratio_threshold and score > best_score:
                best_score = score
                best_col = col

        if best_col is not None:
            aligned_cols.append(best_col)
        else:
            aligned_cols.append(
                ColumnContent(
                    text="",
                    start_indent=t0,
                    end_indent=t1,
                )
            )

    return BlockContent(
        columns=aligned_cols,
        left_indent=block.left_indent,
        right_indent=block.right_indent,
        top_indent=block.top_indent,
        bottom_indent=block.bottom_indent,
    )
