from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

@dataclass
class ColumnInfo:
    left_border: float
    right_border: float

@dataclass
class TableInfo:
    page: int
    columns: list[ColumnInfo]
    horizontal_lines: list[float]

def detect_alignment(
    lines: list[TextBlock],
    left_border: float,
    right_border: float,
    tol: float = 10,
) -> TextAllignment:
    if not lines:
        return TextAllignment.LEFT

    def all_almost_equal(vals: list[float]) -> bool:
        if len(vals) <= 1:
            return True
        base = vals[0]
        return all(abs(v - base) <= tol for v in vals[1:])

    lefts_all = [ln.compute_left_indent(left_border) for ln in lines]
    rights_all = [ln.compute_right_indent(right_border) for ln in lines]

    page_center = (left_border + right_border) / 2.0
    centers = []
    for l, r in zip(lefts_all, rights_all):
        line_left = left_border + l
        line_right = right_border - r
        centers.append((line_left + line_right) / 2.0)

    if all(abs(c - page_center) / (right_border - left_border) * 100 <= tol for c in centers):
        return TextAllignment.CENTER


    if len(lines) >= 2:
        body_left = lines[1:]              
        body_right = lines[:-1]            

        lefts_body = [ln.compute_left_indent(left_border) for ln in body_left]
        rights_body = [ln.compute_right_indent(right_border) for ln in body_right]

        left_equal = all_almost_equal(lefts_body)
        right_equal = all_almost_equal(rights_body)

        if left_equal and right_equal:
            return TextAllignment.WIDTH
        else:
            if left_equal:
                return TextAllignment.LEFT
            else:
                if right_equal:
                    return TextAllignment.RIGHT
    else:
        left_indent = lefts_all[0]
        right_indent = rights_all[0]

        if abs(left_indent) <= tol:
            return TextAllignment.LEFT
        if abs(right_indent) <= tol:
            return TextAllignment.RIGHT

    return TextAllignment.LEFT


def group_columns(line_blocks: List[LineBlock]) -> list[list[TextBlock]]:
    if not line_blocks:
        return []
    n_cols = len(line_blocks[0].text_blocks)
    cols = [[] for _ in range(n_cols)]
    for lb in line_blocks:
        for i, tb in enumerate(lb.text_blocks):
            cols[i].append(tb)
    return cols

def is_same_paragraph(prev_tbs: list[TextBlock], cur_tb: TextBlock, x_tol: float = 0.5):
    if not prev_tbs:
        return True
    last_tb = prev_tbs[-1]
    if last_tb.style != cur_tb.style:
        return False

    last_text = last_tb.text.strip()
    cur_text = cur_tb.text.strip()

    if cur_text and (cur_text[0].islower() or last_text.endswith("-")):
        return True
    
    body_for_left = prev_tbs[1:]

    if not body_for_left:
        if cur_tb.bbox.x0 < last_tb.bbox.x0 - x_tol:
            return True
        if abs(cur_tb.bbox.x0 - last_tb.bbox.x0) < x_tol:
            return True
        return False
    
    p_x0 = min(tb.bbox.x0 for tb in body_for_left)
    p_x1 = max(tb.bbox.x1 for tb in prev_tbs)

    if (cur_tb.bbox.x0 - p_x0) >= x_tol:
        return False
    
    is_last_incomplete = (p_x1 - last_tb.bbox.x1) >= x_tol
    if is_last_incomplete:
        return False
    
    is_left_aligned = all(abs(tb.bbox.x0 - p_x0) < x_tol for tb in body_for_left)
    is_right_aligned = all(abs(tb.bbox.x1 - p_x1) < x_tol for tb in prev_tbs)

    first_line_indent = prev_tbs[0].bbox.x0 - p_x0
    if abs((cur_tb.bbox.x0 - p_x0) - first_line_indent) < x_tol:
        return False
    
    if is_left_aligned:
        if abs(cur_tb.bbox.x0 - p_x0) < x_tol:
            return True
        if cur_tb.bbox.x0 > p_x0 + x_tol:
            return False
        
    if is_right_aligned:
        if abs(cur_tb.bbox.x1 - p_x1) < x_tol:
            return True
        return False
    
    return abs(cur_tb.bbox.x0 - p_x0) < x_tol


def split_column_to_paragraphs(column: list[TextBlock]) -> list[list[TextBlock]]:
    result = []
    blocks_iter = iter(tb for tb in column if not tb.is_empty())
    first_tb = next(blocks_iter, None)
    if first_tb is None:
        return []

    current_paragraph = [first_tb]

    for tb in blocks_iter:
        if is_same_paragraph(current_paragraph, tb):
            current_paragraph.append(tb)
        else:
            result.append(current_paragraph)
            current_paragraph = [tb]

    result.append(current_paragraph)
    return result


@dataclass
class Bbox:
    x0: float
    y0: float
    x1: float
    y1: float

@dataclass
class BlockCoordinate:
    start_page: int
    start_block: int

@dataclass(frozen=True)
class Style:
    font: str
    size: float
    color: int

    def __eq__(self, other):
        return (
            self.font == other.font and
            self.size == other.size and
            self.color == other.color
        )
    
@dataclass
class ParagraphStyle:
    style: Style
    left_indent: float
    text_alignment: TextAllignment
    spacing: float


class BlockType(Enum):
    TITLE = 1
    TOC = 2
    SECTION = 4
    APPENDIX = 5
    TABLE = 6
    PICTURE = 7
    PARAGRAPH = 8


class TextAllignment(Enum):
    LEFT = 1
    CENTER = 2
    RIGHT = 3
    WIDTH = 4

@dataclass
class Block:
    id: int
    start: BlockCoordinate


@dataclass
class BlockInfo:
    id: int
    block: Block
    subblocks: list


@dataclass
class TextBlock:
    text: str
    bbox: Bbox
    style: Style

    def compute_left_indent(self, left_border: float):
        return self.bbox.x0 - left_border
    
    def compute_right_indent(self, right_border: float):
        return right_border - self.bbox.x1
    
    def is_empty(self) -> bool:
        return not self.text


@dataclass
class LineBlock:
    text_blocks: list[TextBlock]
    bbox: Bbox

    def compute_left_indent(self, left_border: float):
        return self.bbox.x0 - left_border
    
    def compute_right_indent(self, right_border: float):
        return right_border - self.bbox.x1
    
    def text(self):
        return " ".join(tb.text for tb in self.text_blocks if tb.text).strip()


@dataclass
class ParagraphBlock(Block):
    #line_blocks: list[LineBlock]        # Поле потенциально нужное только для вычисления всего остального
    bbox: Bbox = None
    main_style: ParagraphStyle = None
    text: str = None

    def __init__(self, id: int, coord: BlockCoordinate, lines: list[TextBlock], left_border: float, right_border: float):
        self.id = id
        self.start = coord
        left_indent = None
        spacing = 0.0
        main_style = None

        lines_text: str = ""
        for line in lines:
            text = line.text.strip()
            lines_text = (lines_text[:-1] if lines_text.endswith("-") else lines_text + (" " if lines_text else "")) + text
        self.text = lines_text

        if lines:
            x0 = min(lb.bbox.x0 for lb in lines)
            y0 = min(lb.bbox.y0 for lb in lines)
            x1 = max(lb.bbox.x1 for lb in lines)
            y1 = max(lb.bbox.y1 for lb in lines)
            self.bbox = Bbox(x0, y0, x1, y1)

        # Определяем отступ первой строки
        if lines:
            first_line = lines[0]
            left_indent = max(0.0, first_line.bbox.x0 - left_border)

        # Определяем выравнивание
        text_allignment = detect_alignment(lines, left_border, right_border)

        # Вычисляем междустрочный интервал
        if len(lines) >= 2:
            ys = sorted(lb.bbox.y0 for lb in lines)
            diffs = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
            if diffs:
                spacing = sum(diffs) / len(diffs)

        # Определяем основной стиль абзаца
        style_weights: dict[Style, int] = defaultdict(int)
        for tb in lines:
            if tb.text and tb.style:
                style_weights[tb.style] += len(tb.text)

        if style_weights:
            main_style = max(style_weights.items(), key=lambda kv: kv[1])[0]
        
        self.main_style = ParagraphStyle(
            main_style,
            left_indent,
            text_allignment,
            spacing
        )

@dataclass
class TableCell:
    left_border: float
    right_border: float
    subblocks: list

    def __init__(self, column_info: ColumnInfo, column: list[TextBlock]):
        self.subblocks = []
        self.left_border = column_info.left_border
        self.right_border = column_info.right_border
        paragraphs = split_column_to_paragraphs(column)
        for paragraph in paragraphs:
            p = ParagraphBlock(
                0,
                BlockCoordinate(0, 0),
                paragraph,
                self.left_border,
                self.right_border
            )
            self.subblocks.append(p)

@dataclass
class TableRow:
    cells: list[TableCell]

    def __init__(self, column_info: ColumnInfo, columns: list[list[TextBlock]]):
        self.cells = [TableCell(column_info[i], columns[i]) for i in range(len(columns))]

@dataclass
class TableBlock(Block):
    rows: list[TableRow]


@dataclass
class TitleBlock:
    university: Optional[str] = None
    faculty: Optional[str] = None
    practice_type: Optional[str] = None
    student: Optional[str] = None
    supervisor: Optional[str] = None
    student_group: Optional[str] = None
    supervisor_position: Optional[str] = None
    major: Optional[str] = None
    specialization: Optional[str] = None
    year: Optional[int] = None


@dataclass
class TocEntry:
    title: str
    page: int
    raw_text: str
    block: Block = None


@dataclass 
class TocBlock(Block):
    entries: dict[str, TocEntry]

@dataclass
class SectionBlock(Block):
    title: ParagraphBlock
    level: int
    subblocks: list[Block]

@dataclass
class Caption:
    number: int
    title: str
    block: ParagraphBlock

@dataclass
class DocumentBlock:
    toc: TocBlock
    title: TitleBlock
    subblocks: list[Block]
    table_captions: list[Caption] = None
    figure_captions: list[Caption] = None
