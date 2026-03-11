from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


def detect_alignment(
    lines: list[LineBlock],
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
    style: ParagraphStyle = None
    text: str = None

    def __init__(self, coord: BlockCoordinate, line_blocks: list[LineBlock], left_border: float, right_border: float):
        self.start = coord
        left_indent = None
        spacing = 0.0
        main_style = None
        
        lines_text: List[str] = []
        for line in line_blocks:
            parts = [tb.text for tb in line.text_blocks if tb.text]
            line_text = "".join(parts).rstrip()
            if line_text:
                lines_text.append(line_text)
        self.text = "\n".join(lines_text)

        if line_blocks:
            x0 = min(lb.bbox.x0 for lb in line_blocks)
            y0 = min(lb.bbox.y0 for lb in line_blocks)
            x1 = max(lb.bbox.x1 for lb in line_blocks)
            y1 = max(lb.bbox.y1 for lb in line_blocks)
            self.bbox = Bbox(x0, y0, x1, y1)

        # Определяем отступ первой строки
        if line_blocks:
            first_line = line_blocks[0]
            left_indent = max(0.0, first_line.bbox.x0 - left_border)

        # Определяем выравнивание
        text_allignment = detect_alignment(line_blocks, left_border, right_border)

        # Вычисляем междустрочный интервал
        if len(line_blocks) >= 2:
            ys = sorted(lb.bbox.y0 for lb in line_blocks)
            diffs = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
            if diffs:
                spacing = sum(diffs) / len(diffs)

        # Определяем основной стиль абзаца
        style_weights: dict[Style, int] = defaultdict(int)
        for line in line_blocks:
            for tb in line.text_blocks:
                if tb.text and tb.style:
                    w = len(tb.text)
                    style_weights[tb.style] += w

        if style_weights:
            main_style = max(style_weights.items(), key=lambda kv: kv[1])[0]
        
        self.main_style = ParagraphStyle(
            main_style,
            left_indent,
            text_allignment,
            spacing
        )


@dataclass
class TableRow:
    line_blocks: list[LineBlock]
    bbox: Bbox


@dataclass
class ColumnInfo:
    title: str
    left_indent: float
    right_indent: float

@dataclass
class TableCell:
    left_indent: float
    right_indent: float
    subblocks: list

@dataclass
class TableBlock(Block):
    column_info: list[ColumnInfo]       
    raw_rows: list[TableRow]            # Это поле нужно для подсчета нормальных ячеек
    rows: list[list[TableCell]]


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
    table_captions: list[Caption]
    figure_captions: list[Caption]
