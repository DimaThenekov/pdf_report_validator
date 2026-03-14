import json

import pymupdf
import pymupdf.layout  # Важно: импорт активирует "умный" режим
import pymupdf4llm

# Теперь функции из pymupdf4llm будут использовать Layout-анализ
md_text = pymupdf4llm.to_markdown("Марухленко И. С. дз 5.pdf")
json_data = pymupdf4llm.to_json("Марухленко И. С. дз 5.pdf")

if isinstance(json_data, str):
    json_data = json.loads(json_data)

with open("output.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, indent=4, ensure_ascii=False)


import fitz

doc = fitz.open("Марухленко_И_С_Лабораторная_работа_3_Взрыв_2023.pdf")
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
