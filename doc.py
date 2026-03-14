import json

import pymupdf
import pymupdf.layout  # Важно: импорт активирует "умный" режим
import pymupdf4llm


import fitz

doc = fitz.open("Пронина А. И. Отчет по учебной практике P3433.pdf")
for page in doc:
    # Извлекаем структуру
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if "lines" in b:
            # Красная рамка вокруг БЛОКА
            page.draw_rect(b["bbox"], color=(1, 0, 0), width=1)
            for l in b["lines"]:
                # Синяя рамка вокруг ЛИНИИ
                page.draw_rect(l["bbox"], color=(0, 0, 1), width=0.5)

doc.save("debug_layout.pdf")
