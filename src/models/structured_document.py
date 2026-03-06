from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class StructuredDocument:
    blocks: list[BlockInfo]

class BlockType(Enum):
    TITLE = 1
    CHAPTER = 2
    SECTION = 3
    APPENDIX = 4
    TABLE = 5
    PICTURE = 6
    PARAGRAPH = 7

# output of type_parser, input for parsers_matcher
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