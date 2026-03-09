from src.models.structured_document import StructuredDocument

from ..models.structured_document import (
    BlockInfo,
    BlockType,
    ParagraphMetainfo,
    SectionMetainfo,
    TableMetainfo,
    TableRowEntry,
    TitleMetainfo,
    TocMetainfo,
    TocEntry,
)

from src.type_parser.title_parser import *
from src.type_parser.utils import *

class TypeParser:

    def __init__(self):
        self.id_counter = 1
        self.current_page = 1
        self.current_block = 0
        self.current_line = 0
        self.current_table = 0
        self.toc = None
        self.heading_styles = []
        self.main_style = None

    def next_id(self):
        temp = self.id_counter
        self.id_counter += 1
        return temp
    
    def inc(self, pages):
        if self.current_block + 1 == len(pages[self.current_page].get("blocks", [])):
            self.current_page += 1
            self.current_block = 0
        else:
            self.current_block += 1


    def parse_document(self, document):
        self.pages = document
        pages = [page.get_text("dict", sort=True) for page in document]

        self.main_style = compute_body_main_style(pages)
        result = StructuredDocument()

        title_page = pages[0]
        title = self.parse_title(title_page)
        result.blocks.append(title)

        while self.current_page < len(pages):
            page_idx = self.current_page
            page = pages[page_idx]
            blocks = page.get("blocks", [])
            while self.current_block < len(blocks):
                block_idx = self.current_block
                block = blocks[block_idx]
                if not self.toc and is_toc_title_block(block):
                    toc_block = self.parse_toc_multi_page_blocks(
                        pages
                    )
                    self.toc = toc_block
                    result.blocks.append(self.toc)
                else:
                    if is_heading_candidate(block, self.toc, self.main_style):
                        style = get_block_main_style(block)
                        level = check_heading_style(style, self.heading_styles)
                        if (level == -1):
                            level = len(self.heading_styles)
                            self.heading_styles.append(style)
                        section_block = self.parse_section(
                            pages,
                            level
                        )
                        result.blocks.append(section_block)
                    else:
                        if block_idx + 1 == len(blocks):
                            self.current_page += 1
                            self.current_block = 0
                        else:
                            self.current_block += 1

                if (page_idx < self.current_page):
                    break
                else:
                    continue


        return result
    

    def parse_toc_multi_page_blocks(
        self,
        pages: list[dict],
    ) -> BlockInfo:
        
        entries: dict[str, TocEntry] = {}

        page_idx = self.current_page
        block_idx = self.current_block + 1 

        def _make_toc_block(entries: list[TocEntry]) -> BlockInfo:
            meta = TocMetainfo(entries=entries)
            return BlockInfo(
                id=self.next_id(),  
                type=BlockType.TOC,
                metainfo=meta,
                subblocks=[],
            )

        while page_idx < len(pages):
            page = pages[page_idx]
            blocks = page.get("blocks", [])

            while block_idx < len(blocks):
                block = blocks[block_idx]
                text = get_block_single_line_text(block)

                if not text:
                    block_idx += 1
                    continue

                parsed = parse_toc_entry_block(block)
                if parsed is not None:
                    entries[parsed.title.lower()] = parsed
                    block_idx += 1
                    continue

                self.current_page = page_idx
                self.current_block = block_idx
                return _make_toc_block(entries)

            page_idx += 1
            block_idx = 0

        self.current_page = page_idx
        self.current_block = block_idx
        return _make_toc_block(entries)


    def parse_title(self, page: dict) -> BlockInfo:
        page_width = page["width"]

        meta = TitleMetainfo()

        for line in iter_lines(page):
            text = line["text"].strip()
            print(text)

            # университет
            if meta.university is None:
                u = detect_university(line)
                if u:
                    meta.university = u
                    continue

            # факультет
            if meta.faculty is None:
                f = detect_faculty(line)
                if f:
                    meta.faculty = f
                    continue

            # студент (ФИО + группа)
            if meta.student_full_name is None or meta.student_group is None:
                st = match_student(text)
                if st:
                    if meta.student_group is None:
                        meta.student_group = st["student_group"]
                        meta.practice_type = detect_practice_type(st["student_group"])
                    if meta.student_full_name is None:
                        meta.student_full_name = st["student_full_name"]
                    continue

            # руководитель
            if meta.supervisor_full_name is None:
                sup = match_supervisor(text)
                if sup:
                    meta.supervisor_full_name = sup["supervisor_full_name"]
                    # при желании здесь же можно попытаться выделить должность
                    continue

            # направление
            if meta.major is None:
                maj = match_major(text)
                if maj:
                    meta.major = maj["major"]
                    continue

            # специальность / профиль
            if meta.specialization is None:
                spec = match_specialization(text)
                if spec:
                    meta.specialization = spec["specialization"]
                    continue

            # год
            if meta.year is None:
                y = detect_year(line)
                if y:
                    meta.year = y
                    continue


        block = BlockInfo(
            id=self.next_id(),
            type=BlockType.TITLE,
            metainfo=meta,
            subblocks=[],
        )
        return block
    
    def parse_section(self, pages: list[dict], level: int) -> BlockInfo:
        block = pages[self.current_page].get("blocks", [])[self.current_block]
        text = get_block_single_line_text(block)
        meta = SectionMetainfo(
            title = text.strip().lower(),
            level=level,
            font_stats=get_block_font_stats(block),
            style=get_block_main_style(block)
        )
        subblocks = []
        self.inc(pages)

        while (self.current_page < len(pages)):
            page = pages[self.current_page]
            blocks = page.get("blocks", [])
            block = blocks[self.current_block]
            if (is_heading_candidate(block, self.toc, self.main_style)):
                style = get_block_main_style(block)
                new_level = check_heading_style(style, self.heading_styles)
                if (new_level == -1):
                    new_level = len(self.heading_styles)
                    self.heading_styles.append(style)
                if new_level <= level:
                    return BlockInfo(
                        self.next_id(),
                        type=BlockType.SECTION,
                        metainfo=meta,
                        subblocks=subblocks
                    )
                section_block = self.parse_section(
                    pages,
                    level
                )
                subblocks.append(section_block)
            else:
                if is_table_start(block):
                    table_meta = parse_table_start(self.pages[self.current_page].find_tables()[self.current_table])
                    self.current_table += 1
                    self.parse_table(pages, table_meta)
                    table_block = BlockInfo(
                        self.next_id(),
                        BlockType.TABLE,
                        metainfo=table_meta,
                        subblocks=[]
                    )
                    subblocks.append(table_block)
                else:
                    if is_paragraph_start(block, self.main_style):
                        paragraph_block = self.parse_paragraph(
                            pages
                        )
                        subblocks.append(paragraph_block)

        return BlockInfo(
            self.next_id(),
            type=BlockType.SECTION,
            metainfo=meta,
            subblocs=subblocks
        )
    

    def parse_table(self, pages: list[dict], meta: TableMetainfo, min_gap: float = 8):
        block = pages[self.current_page].get("blocks", [])[self.current_block]
        column_info = meta.column_info
        prev_block = align_block_to_columns(build_block_content(block), column_info)
        rows = []
        self.inc(pages)

        while (self.current_page < len(pages)):
            blocks = pages[self.current_page].get("blocks", [])
            block = align_block_to_columns(build_block_content(blocks[self.current_block]), column_info)
            if (block.top_indent > prev_block.bottom_indent):
                diff = block.top_indent - prev_block.bottom_indent
                if (diff > min_gap):
                    rows.append(prev_block)
                    prev_block = block
                else:
                    prev_block += block
            else:
                prev_block = block
            self.inc(pages)


    def parse_paragraph(self, pages: list[dict]) -> BlockInfo:
        block = pages[self.current_page].get("blocks", [])[self.current_block]
        full_text = get_block_single_line_text(block)
        description = get_block_font_stats(block)
        style = get_block_main_style(block)
        self.inc(pages)

        while (self.current_page < len(pages)):
            page = pages[self.current_page]
            blocks = page.get("blocks", [])
            block = blocks[self.current_block]
            if (continues_paragraph(block, self.main_style)):
                text = get_block_single_line_text(block)
                full_text += text
                description += get_block_font_stats(block)
            else:
                meta = ParagraphMetainfo(
                    full_text=" ".join(full_text.split()).strip(),
                    style=description.get_style(),
                    start_indent=style.indent_left
                )
                return BlockInfo(
                    id=self.next_id(),
                    type=BlockType.PARAGRAPH,
                    metainfo=meta,
                    subblocks=[]
                )
            self.inc(pages)

        meta = ParagraphMetainfo(
            full_text=" ".join(full_text.split()).strip(),
            style=description.get_style(),
            start_indent=style.indent_left
        )
        return BlockInfo(
            id=self.next_id(),
            type=BlockType.PARAGRAPH,
            metainfo=meta,
            subblocks=[]
        )
