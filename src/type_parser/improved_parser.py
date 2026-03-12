import fitz
from pymupdf import Document

from src.models.parsed_pdf import *
from src.type_parser.utils2 import *

class PdfParser:

    def collect_tables(self, doc: Document) -> list[list[TableInfo]]:
        all_pages: list[list[TableInfo]] = []
        for i, page in enumerate(doc):
            page_tables: list[TableInfo] = []
            for tab in page.find_tables():
                header = tab.header
                columns = []
                ys = set()
                for j in range(len(header.cells)):
                    x0, y0, x1, y1 = header.cells[j]
                    columns.append(ColumnInfo(x0, x1))
                for row in tab.rows:
                    x0, y0, x1, y1 = row.bbox
                    ys.add(y0)
                    ys.add(y1)
                page_tables.append(
                    TableInfo(
                        i,
                        columns,
                        sorted(ys)
                    )
                )
            all_pages.append(page_tables)
        return all_pages


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
            RawBlockType.TOC_CAPTION: self.parse_toc,
            RawBlockType.UNUSED: lambda: None
        }
        self.last_heading = None
        self.tables = self.collect_tables(doc)

    def group_columns(self, line_blocks: List[LineBlock]) -> list[list[TextBlock]]:
        if not line_blocks:
            return []
        n_cols = len(line_blocks[0].text_blocks)
        cols = [[] for _ in range(n_cols)]
        for lb in line_blocks:
            for i, tb in enumerate(lb.text_blocks):
                cols[i].append(tb)
        return cols
    
    def get_heading_level(self, pstyle: ParagraphStyle, tol: float = 1.5) -> int:
        for i, existing in enumerate(self.heading_styles):
            if existing.text_alignment == pstyle.text_alignment and existing.style == pstyle.style:
                indent_ok = pstyle.text_alignment == TextAllignment.CENTER or abs(existing.left_indent - pstyle.left_indent) <= tol
                spacing_ok = abs(existing.spacing - pstyle.spacing) <= tol
                
                if indent_ok and spacing_ok:
                    return i + 1
        self.heading_styles.append(pstyle)
        return len(self.heading_styles)
    
    def split_line_into_columns(self, line: LineBlock) -> LineBlock:
        table = self.get_current_table()
        blocks_iter = iter(line.text_blocks)
        current_b = next(blocks_iter, None)
        result: list[TextBlock] = []
        
        default_style = line.text_blocks[0].style if line.text_blocks else Style()

        for col in table.columns:
            col_group = []
            
            while current_b and current_b.bbox.x1 <= col.left_border:
                current_b = next(blocks_iter, None)

            while current_b and current_b.bbox.x0 < col.right_border:
                col_group.append(current_b)
                current_b = next(blocks_iter, None)

            if col_group:
                text = " ".join(b.text.strip() for b in col_group if b.text)
                new_bbox = Bbox(
                    x0=min(b.bbox.x0 for b in col_group),
                    y0=min(b.bbox.y0 for b in col_group),
                    x1=max(b.bbox.x1 for b in col_group),
                    y1=max(b.bbox.y1 for b in col_group)
                )
                result.append(TextBlock(text, new_bbox, col_group[0].style))
            else:
                res_bbox = Bbox(col.left_border, line.bbox.y0, col.right_border, line.bbox.y1)
                result.append(TextBlock("", res_bbox, default_style))

        return LineBlock(text_blocks=result, bbox=line.bbox)
    
    def get_raw_block_type(self, block: dict):
        if block.get("image"):
            return RawBlockType.FIGURE
        line = split_block_into_lineblock(block)
        if (len(line.text_blocks) == 0):
            return RawBlockType.UNUSED
        line_block = self.split_line_into_columns(line)
        if len(line_block.text_blocks) > 1:
            return RawBlockType.TABLE
        block_text = line.text().strip()
        if TOC_CAPTION_RE.match(block_text):
            return RawBlockType.TOC_CAPTION
        if PAGE_NUMBER_RE.match(block_text.strip()):
            return RawBlockType.UNUSED
        return RawBlockType.TEXT

    def get_current_table(self):
        block = self.pages[self.current_page].get("blocks", [])[self.current_block]
        top = block["bbox"][1]
        bottom = block["bbox"][3]
        for table in self.tables[self.current_page]:
            if table.horizontal_lines[0] <= (top + bottom) / 2 and table.horizontal_lines[-1] >= (top + bottom) / 2:
                return table
        
        width = self.pages[self.current_page]["width"]
        height = self.pages[self.current_page]["height"]
        return TableInfo(
            self.current_page,
            [ColumnInfo(0, width)],
            [0, height]
        )

    def next_id(self):
        temp = self.id_counter
        self.id_counter += 1
        return temp
    
    def inc(self):
        if self.current_block + 1 == len(self.pages[self.current_page].get("blocks", [])):
            self.current_page += 1
            self.current_block = 0
            self.current_table = 0
        else:
            self.current_block += 1
    
    def parse_document(self) -> DocumentBlock:
        title = self.parse_title(self.pages[0])
        toc = None
        subblocks = []

        while (self.current_page < self.pages_count):
            page = self.pages[self.current_page]
            block = page.get("blocks", [])[self.current_block]
            block_type = self.get_raw_block_type(block)
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
            block_type = self.get_raw_block_type(block)
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

    def parse_table_row(self, table) -> list[LineBlock]:
        page_idx = self.current_page
        page = self.pages[page_idx]
        blocks = page.get("blocks", [])
        line_blocks = []

        while self.current_page == page_idx:
            block = blocks[self.current_block]
            block_type = self.get_raw_block_type(block)
            if (block_type == RawBlockType.UNUSED):
                self.inc()
                continue
            if block_type not in [RawBlockType.TEXT, RawBlockType.TABLE]:
                break
            line = split_block_into_lineblock(block)
            line_block = self.split_line_into_columns(line)
            if line_blocks:
                prev_block = line_blocks[-1]
                if has_between(table.horizontal_lines, (prev_block.bbox.y0 + prev_block.bbox.y1) / 2, (line_block.bbox.y0 + line_block.bbox.y1) / 2):
                    break
            line_blocks.append(line_block)
            self.inc()
        
        return line_blocks


    def parse_table(self) -> TableBlock:
        start_page = self.current_page
        start_block = self.current_block
        rows = []

        while self.current_page < self.pages_count:
            table = self.get_current_table()
            page = self.pages[self.current_page]
            block = page.get("blocks", [])[self.current_block]
            block_type = self.get_raw_block_type(block)
            if block_type == RawBlockType.UNUSED:
                self.inc()
                continue
            if block_type == RawBlockType.TEXT:
                paragraph = self.parse_paragraph()
                if is_table_continuation(paragraph):
                    continue
                self.current_page = paragraph.start.start_page
                self.current_block = paragraph.start.start_block
                break
            if block_type != RawBlockType.TABLE:
                break
            
            table_row = self.parse_table_row(table)
            if not table_row:
                break
            grouped_columns = group_columns(table_row)
            row = TableRow(
                table.columns,
                grouped_columns
            )
            rows.append(row)
    
        return TableBlock(
            self.next_id(),
            BlockCoordinate(
                start_page, 
                start_block
            ),
            rows
        )
                
            
    def parse_paragraph(self) -> ParagraphBlock:
        page = self.pages[self.current_page]
        start_page = self.current_page
        start_block = self.current_block

        paragraph_blocks = []
        
        while self.current_page < self.pages_count:
            page = self.pages[self.current_page]
            block = page.get("blocks", [])[self.current_block]
            block_type = self.get_raw_block_type(block)
            if block_type != RawBlockType.TEXT:
                break
            line_block = self.split_line_into_columns(split_block_into_lineblock(block))
            text_block = line_block.text_blocks[0]
            if not is_same_paragraph(paragraph_blocks, text_block):
                break
            paragraph_blocks.append(text_block)
            self.inc()

        return ParagraphBlock(
            self.next_id(),
            BlockCoordinate(
                start_page,
                start_block
            ),
            paragraph_blocks,
            0,
            page.get("width")
        )

    