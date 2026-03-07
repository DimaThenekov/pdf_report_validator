import re
from typing import Any, Counter, Dict

from src.models.structured_document import BlockInfo, HeadingStyle

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

def is_toc_title_block(block: dict) -> bool:
    text = get_block_text(block)
    return any(w in text.lower() for w in TOC_TITLE_WORDS)

def get_block_text(block: dict) -> str:
    parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            parts.append(span.get("text", ""))
    raw = "".join(parts)
    text = re.sub(r"\s+", " ", raw).strip()
    return text


def get_block_font_stats(block: dict) -> dict:
    sizes = []
    fonts = []
    colors = []

    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "")
            if not SPACE_RE.sub("", text):
                continue

            s = span.get("size")
            f = span.get("font")
            c = span.get("color")

            if s:
                sizes.append(round(s, 1))
            if f:
                fonts.append(f)
            if c is not None:
                colors.append(c)

    size = max(sizes) if sizes else None
    font = Counter(fonts).most_common(1)[0][0] if fonts else None
    color = Counter(colors).most_common(1)[0][0] if colors else None
    return {"size": size, "font": font, "color": color}


def compute_body_style(pages_dicts: list[dict]) -> dict:
    sizes = []
    fonts = []
    for page in pages_dicts:
        for block in page.get("blocks", []):
            txt = get_block_text(block)
            if not txt:
                continue
            stats = get_block_font_stats(block)
            if stats["size"]:
                sizes.append(stats["size"])
            if stats["font"]:
                fonts.append(stats["font"])
    body_size = Counter(sizes).most_common(1)[0][0] if sizes else None
    body_font = Counter(fonts).most_common(1)[0][0] if fonts else None
    return {"size": body_size, "font": body_font}


def get_block_single_line_text(block: dict) -> str:
    """Склеиваем все spans блока в одну строку."""
    parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            parts.append(span.get("text", ""))
    raw = "".join(parts)
    text = re.sub(r"\s+", " ", raw).strip()
    return text

def is_toc_entry_block(block: dict) -> bool:
    text = get_block_single_line_text(block)
    if not text:
        return False
    return TOC_BLOCK_RE.match(text) is not None


def parse_toc_entry_block(block: dict) -> dict | None:
    text = get_block_single_line_text(block)
    if not text:
        return None
    m = TOC_BLOCK_RE.match(text)
    if not m:
        return None
    title = m.group("title").strip()
    page = int(m.group("page"))
    return {"title": title, "page": page, "raw": text}


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

def check_heading_style(style: HeadingStyle, styles: list[HeadingStyle]): 
    for i in range(len(styles)):
        if style.font_size == styles[i].font_size:
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
