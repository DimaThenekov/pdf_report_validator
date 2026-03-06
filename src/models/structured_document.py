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
