import fitz
from pymupdf import Document

from src.models.parsed_pdf import *
from src.type_parser.utils2 import PAGE_NUMBER_RE, TOC_BLOCK_RE, RawBlockType, get_raw_block_type, is_heading_candidate, split_block_into_lineblock

class PdfParser:
    def __init__(self, doc: Document):
        self.document = doc
        self.id_counter = 1
        self.current_page = 1
        self.current_block = 0
        self.current_table = 0
        self.toc = None
        self.heading_styles: list[ParagraphStyle] = []
        self.main_style = None
        self.pages = [page.get_text("dict", sort=True) for page in doc]
        self.pages_count = len(self.pages)
        self.dict = {
            RawBlockType.TOC_CAPTION: self.parse_toc,
            RawBlockType.FIGURE: self.parse_figure,
            RawBlockType.TABLE: self.parse_table,
            RawBlockType.TEXT: self.parse_paragraph,
            RawBlockType.TOC_CAPTION: self.parse_toc
        }
        self.last_heading = None

    def get_heading_level(self, pstyle: ParagraphStyle, tol: float = 1.5) -> int:
        for i, existing in enumerate(self.heading_styles):
            if existing.text_alignment == pstyle.text_alignment and existing.style == pstyle.style:
                indent_ok = abs(existing.left_indent - pstyle.left_indent) <= tol
                spacing_ok = abs(existing.spacing - pstyle.spacing) <= tol
                
                if indent_ok and spacing_ok:
                    return i + 1
        self.heading_styles.append(pstyle)
        return len(self.heading_styles)

    def next_id(self):
        temp = self.id_counter
        self.id_counter += 1
        return temp
    
    def inc(self):
        if self.current_block + 1 == len(self.pages[self.current_page].get("blocks", [])):
            self.current_page += 1
            self.current_block = 0
        else:
            self.current_block += 1
    
    def parse_document(self) -> DocumentBlock:
        title = self.parse_title(self.pages[0])
        toc = None
        subblocks = []

        while (self.current_page < self.pages_count):
            page = self.pages[self.current_page]
            block = page.get("blocks", [])[self.current_block]
            block_type = get_raw_block_type(block)
            parsed_block = self.dict[block_type]()
            if not parsed_block:
                self.inc()
                continue
            if (isinstance(parsed_block, ParagraphBlock) and is_heading_candidate(parsed_block, toc)):
                parsed_block = self.parse_section(title=parsed_block)
            if (isinstance(parsed_block, TocBlock)):
                self.toc = parsed_block
                toc = parsed_block
            else:
                subblocks.append(parsed_block)

        return DocumentBlock(
            toc,
            title,
            subblocks
        )


    def parse_title(self, page: dict) -> TitleBlock:
        return TitleBlock()

    def parse_toc(self) -> TocBlock:
        entries: dict[str, TocEntry] = dict()
        start_page = self.current_page
        start_block = self.current_block
        self.inc()
        while self.current_page < self.pages_count:
            page = self.pages[self.current_page]
            block = page.get("blocks", [])[self.current_block]
            line_block = split_block_into_lineblock(block)
            text = line_block.text()
            match = TOC_BLOCK_RE.match(text)
            if match:
                title = match.group("title").strip()
                page_num = int(match.group("page"))
                entry = TocEntry(
                    title=title,
                    page=page_num,
                    raw_text=text             
                )
                entries[title.lower()] = entry
            else:
                if text and not PAGE_NUMBER_RE.match(text):
                    break
            self.inc()
        return TocBlock(
            self.next_id(),
            BlockCoordinate(
                start_page,
                start_block
            ),
            entries
        )


    def parse_section(self, title: ParagraphBlock) -> SectionBlock:
        level = self.get_heading_level(title.main_style)
        start_page = self.current_page
        start_block = self.current_block
        subblocks = []

        while self.current_page < self.pages_count:
            page = self.pages[self.current_page]
            block = page.get("blocks", [])[self.current_block]
            block_type = get_raw_block_type(block)
            parsed_block = self.dict[block_type]()
            if not parsed_block:
                self.inc()
                continue
            if (isinstance(parsed_block, ParagraphBlock) and is_heading_candidate(parsed_block, self.toc)):
                new_level = self.get_heading_level(parsed_block.main_style)
                if (new_level <= level):
                    self.current_page = parsed_block.start.start_page
                    self.current_block = parsed_block.start.start_block
                    break
                parsed_block = self.parse_section(title=parsed_block)
            subblocks.append(parsed_block)
        
        return SectionBlock(
            self.next_id(),
            BlockCoordinate(
                start_page,
                start_block
            ),
            title,
            level, 
            subblocks
        )


    def parse_figure(self) -> FigureBlock:
        pass

    def parse_table(self) -> TableBlock:
        pass

    def parse_paragraph(self) -> ParagraphBlock:
        page = self.pages[self.current_page]
        start_page = self.current_page
        start_block = self.current_block
        first_block = page.get("blocks", [])[self.current_block]
        line_blocks: list[LineBlock] = []
        line_blocks.append(split_block_into_lineblock(first_block))
        self.inc()

        def is_same_paragraph(prev_tb: TextBlock, cur_tb: TextBlock, line_gap_tol: float = 5.0):
            if prev_tb.style != cur_tb.style:
                return False
            if cur_tb.bbox.x0 > prev_tb.bbox.x0:
                return False
            
            v_gap = cur_tb.bbox.y0 - prev_tb.bbox.y1
            if v_gap > line_gap_tol:
                return False
            
            prev_text = prev_tb.text.strip()
            cur_text = cur_tb.text.strip()
            ends_with_terminal = prev_text[-1] in ".!?"
            starts_with_lower = cur_text[0].islower()

            if not ends_with_terminal or starts_with_lower:
                return True
            if prev_text.endswith("-"):
                return True
            return False

        while self.current_page < self.pages_count:
            page = self.pages[self.current_page]
            prev_block = line_blocks[-1]
            block = page.get("blocks", [])[self.current_block]
            block_type = get_raw_block_type(block)
            if block_type != RawBlockType.TEXT:
                break
            line_block = split_block_into_lineblock(block)
            text_block = line_block.text_blocks[0]
            prev_text_block = prev_block.text_blocks[0]
            if not is_same_paragraph(prev_text_block, text_block):
                break
            line_blocks.append(text_block)
            self.inc()

        paragraph = ParagraphBlock(
            self.next_id(),
            BlockCoordinate(
                start_page,
                start_block
            ),
            line_blocks, 
            0, 
            self.pages[0].get("width")
        )
        