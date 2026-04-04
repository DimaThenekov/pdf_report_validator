import re
from typing import List

from src.models.message import MessageCollector


def parse_title_page(lines: List[str], is_magister: bool, messages: MessageCollector) -> None:
    """
    Парсит титульный лист отчета и собирает ошибки/предупреждения.
    """
    if not lines:
        messages.add_error(0, "Титульный лист пуст.")
        return

    # Объединяем все строки для поиска элементов, которые могли быть перенесены
    full_text = " ".join(lines).lower()

    # 1. Проверка шапки и университета
    if "министерство науки и высшего образования" not in full_text:
        messages.add_error(0, "Отсутствует 'Министерство науки и высшего образования Российской Федерации'")
    if "университет итмо" not in full_text and "исследовательский университет итмо" not in full_text:
        messages.add_error(0, "Отсутствует упоминание 'Университет ИТМО'")
    if "программной инженерии и компьютерной техники" not in full_text:
        messages.add_error(0, "Отсутствует или неверно указан факультет (ожидается ПИиКТ)")

    # 2. Проверка направления подготовки
    if "направление подготовки" not in full_text:
        messages.add_error(0, "Отсутствует строка 'Направление подготовки (специальность)'")

    # 3. Проверка заголовка
    if "о т ч е т" not in full_text and "отчет" not in full_text:
        messages.add_error(0, "Отсутствует заголовок 'О Т Ч Е Т'")

    # 4. Проверка соответствия типа работы уровню образования
    if is_magister:
        if "научно-исследовательской" not in full_text:
            messages.add_error(0, "Для магистратуры ожидается 'о научно-исследовательской работе'")
    else:
        if "учебной" not in full_text and "ознакомительной" not in full_text and "производственной" not in full_text:
            messages.add_error(0,
                               "Для бакалавриата ожидается 'об учебной', 'ознакомительной' или 'производственной' практике")

    # Регулярное выражение для поиска группы (Латинская/Кириллическая буква + 4 цифры, например P3433)
    group_pattern = re.compile(r'([A-Za-zА-Яа-я])\s*(\d{4})')

    found_student = False
    found_group = False
    found_supervisor = False
    found_date = False
    found_city = False

    # Построчный анализ для поиска динамических данных
    for i, line in enumerate(lines):
        block_id = i + 1  # Индексация строк с 1 для удобства чтения
        text_lower = line.lower()

        if "обучающийся" in text_lower or "студент" in text_lower:
            found_student = True

        # Поиск группы и проверка курса
        group_match = group_pattern.search(text_lower)
        if group_match:
            found_group = True
            group_letter = group_match.group(1)
            group_digits = group_match.group(2)
            first_digit = group_digits[
                0]  # Первая цифра обычно указывает на уровень (3 - бакалавриат, 4 - магистратура)
            full_group = f"{group_letter}{group_digits}"

            if is_magister and first_digit == '3':
                messages.add_warning(block_id,
                                     f"Номер группы ({full_group}) характерен для бакалавриата, хотя проверяется магистратура")
            elif not is_magister and first_digit == '4':
                messages.add_warning(block_id,
                                     f"Номер группы ({full_group}) характерен для магистратуры, хотя проверяется бакалавриат")

        if "руководитель" in text_lower:
            found_supervisor = True

        if "дата" in text_lower:
            found_date = True

        if "санкт-петербург" in text_lower:
            found_city = True

    # 5. Проверка наличия обязательных блоков, не найденных при построчном обходе
    if not found_student:
        messages.add_error(0, "Не найден блок 'Обучающийся'")
    if not found_group:
        messages.add_error(0, "Не найден номер учебной группы в формате Буква+4 цифры (например, P3433)")
    if not found_supervisor:
        messages.add_error(0, "Не найден блок 'Руководитель практики'")
    if not found_date:
        messages.add_warning(0, "Отсутствует дата (ожидалось слово 'Дата')")
    if not found_city:
        messages.add_error(0, "Отсутствует город 'Санкт-Петербург' в конце титульного листа")