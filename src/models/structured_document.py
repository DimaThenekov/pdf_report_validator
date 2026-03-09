from collections import Counter
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

# output of type_parser, input for parsers_matcher
class StructuredDocument:
    blocks: list[BlockInfo] = []

class BlockType(Enum):
    TITLE = 1
    TOC = 2
    CHAPTER = 3
    SECTION = 4
    APPENDIX = 5
    TABLE = 6
    PICTURE = 7
    PARAGRAPH = 8

@dataclass
class ColumnContent:
    text: str
    start_indent: float
    end_indent: float

    def __add__(self, other: ColumnContent):
        return ColumnContent(
            self.text + other.text,
            min(self.start_indent, other.start_indent),
            max(self.end_indent, other.end_indent)
        )


@dataclass
class BlockContent:
    columns: list[ColumnContent]
    left_indent: float
    right_indent: float
    top_indent: float
    bottom_indent: float

    def __add__(self, other: BlockContent):
        return BlockContent(
            columns=[x + y for x, y in zip(self.columns, other.columns)],
            left_indent=min(self.left_indent, other.left_indent),
            right_indent=max(self.right_indent, other.right_indent),
            top_indent=min(self.top_indent, other.top_indent),
            bottom_indent=max(self.bottom_indent, other.bottom_indent)
        )


@dataclass
class StyleDescription:
    fonts: Counter = field(default_factory=Counter)
    sizes: Counter = field(default_factory=Counter)
    colors: Counter = field(default_factory=Counter)
    left_indents: Counter = field(default_factory=Counter)
    right_indents: Counter = field(default_factory=Counter)

    def __add__(self, other):
        if not isinstance(other, StyleDescription):
            return NotImplemented
        return StyleDescription(
            fonts=self.fonts + other.fonts,
            sizes=self.sizes + other.sizes,
            colors=self.colors + other.colors,
            left_indents=self.left_indents + other.left_indents,
            right_indents=self.right_indents + other.right_indents,
        )
    
    def get_style(self):
        return Style(
            main_font=self.fonts.most_common(1)[0][0] if self.fonts else None,
            main_size=self.sizes.most_common(1)[0][0] if self.sizes else None,
            main_color=self.colors.most_common(1)[0][0] if self.colors else None
        )
    
@dataclass
class Style:
    main_font: str
    main_size: float
    main_color: int
    
@dataclass
class BlockStyle(Style):
    indent_left: float
    indent_right: float
    
@dataclass
class DocumentStyle(Style):
    description: StyleDescription
    min_indent_left: float
    max_indent_left: float
    min_indent_right: float
    max_indent_right: float

    def __init__(self, desc: StyleDescription):
        self.styles = desc
        self.main_size = desc.sizes.most_common(1)[0][0] if desc.sizes else None
        self.main_font = desc.fonts.most_common(1)[0][0] if desc.fonts else None
        self.main_color = desc.colors.most_common(1)[0][0] if desc.colors else None
        self.min_indent_left = min(desc.left_indents)
        self.max_indent_left = max(desc.left_indents)
        self.min_indent_right = min(desc.right_indents)
        self.max_indent_right = max(desc.right_indents)

@dataclass
class BlockInfo:
    id: int
    type: BlockType
    metainfo: BlockMetainfo
    subblocks: list[BlockInfo]

class BlockMetainfo:
    pass

@dataclass
class TitleMetainfo(BlockMetainfo):
    university: Optional[str] = None
    faculty: Optional[str] = None
    practice_type: Optional[str] = None
    student_full_name: Optional[str] = None
    supervisor_full_name: Optional[str] = None
    student_group: Optional[str] = None
    supervisor_position: Optional[str] = None
    major: Optional[str] = None
    specialization: Optional[str] = None
    year: Optional[int] = None

@dataclass
class TocEntry:
    title: str
    target_page: str
    raw_line: str

@dataclass
class TocMetainfo(BlockMetainfo):
    entries: dict[str, TocEntry]

@dataclass
class SectionMetainfo(BlockMetainfo):
    title: str = None
    level: int = None
    font_stats: dict = None
    style: BlockStyle = None

@dataclass
class ParagraphMetainfo(BlockMetainfo):
    full_text: str = None
    style: Style = None
    start_indent: float = None

@dataclass
class ColumnInfo:
    name: str
    left_indent: str
    right_indent: str

@dataclass
class TableMetainfo(BlockMetainfo):
    columns_count: int = None
    column_info: list[ColumnInfo] = field(default_factory=list)
    rows: list[BlockContent] = field(default_factory=list)
    indent_left: float = None
    indent_right: float = None

@dataclass
class TableColumn:
    full_text: str
    indent_left: float
    indent_right: float

@dataclass
class TableRowEntry:
    column_values: list[TableColumn]
    def __init__(self, columns):
        self.column_values = sorted(columns, key=lambda x: x.indent_left)

# ==========================================================

class Parser(Enum):
    NONE = 0
    
    # Бакалавры
    INTRODUCTION = 1                 # Введение
    STAGE_DESCRIPTION = 2            # Описание выполнения этапов
    LECTURES = 3                     # Лекции
    THESIS_TEMPLATE = 4              # Шаблон для вкр
    TECHNICAL_TASK = 5               # Техническое задание
    CONCLUSION = 6                   # Заключение
    REFERENCES = 7                   # Список литературы
    APPENDIX_A = 8                   # Приложение А
    APPENDIX_B = 9                   # Приложение Б

    # Магистры
    MAG_INTRODUCTION = 101            # Введение
    DOMAIN_ANALYSIS = 102             # Анализ предметной области
    MODEL_DESIGN = 103                # Проектирование модели
    MODEL_IMPLEMENTATION = 104        # Реализация модели
    TESTING_RESEARCH = 105            # Тестирование и исследование
    MAG_CONCLUSION = 106              # Заключение

# output of parsers_matcher, input for parsers
@dataclass
class FlatBlocks:
    parser: Parser # seted by parsers_matcher
    blocks: list[FlatBlockInfo]

@dataclass
class FlatBlockInfo:
    id: int
    type: BlockType
    metainfo: BlockMetainfo