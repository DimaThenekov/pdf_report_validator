from typing import List, Union, Optional
from dataclasses import dataclass
from enum import Enum


class MessageType(str, Enum):
    """Типы сообщений"""
    ERROR = "errors"
    WARNING = "warnings"


@dataclass
class Message:
    """Базовый класс для сообщения"""
    block_id: int
    type: MessageType
    text: str
    
    def __post_init__(self):
        """Валидация после инициализации"""
        if not isinstance(self.block_id, int) or self.block_id < 0:
            raise ValueError("block_id должен быть неотрицательным целым числом")
        if not self.text or not isinstance(self.text, str):
            raise ValueError("text должен быть непустой строкой")
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "blockId": self.block_id,
            "type": self.type.value,
            "text": self.text
        }


class Error(Message):
    """Класс для ошибки"""
    def __init__(self, block_id: int, text: str):
        super().__init__(block_id, MessageType.ERROR, text)


class Warning(Message):
    """Класс для предупреждения"""
    def __init__(self, block_id: int, text: str):
        super().__init__(block_id, MessageType.WARNING, text)


class MessageCollector:
    """
    Класс для сбора и управления сообщениями (ошибок и предупреждений)
    """
    
    def __init__(self):
        self._messages: List[Message] = []
    
    def add_error(self, block_id: int, text: str) -> None:
        """Добавление ошибки"""
        self._messages.append(Error(block_id, text))
    
    def add_warning(self, block_id: int, text: str) -> None:
        """Добавление предупреждения"""
        self._messages.append(Warning(block_id, text))
    
    def add_message(self, message: Message) -> None:
        """Добавление готового сообщения"""
        if not isinstance(message, Message):
            raise TypeError("message должен быть экземпляром класса Message")
        self._messages.append(message)
    
    def get_errors(self) -> List[Error]:
        """Получение всех ошибок"""
        return [msg for msg in self._messages if msg.type == MessageType.ERROR]
    
    def get_warnings(self) -> List[Warning]:
        """Получение всех предупреждений"""
        return [msg for msg in self._messages if msg.type == MessageType.WARNING]
    
    def get_all_messages(self) -> List[Message]:
        """Получение всех сообщений"""
        return self._messages.copy()
    
    def get_messages_by_block(self, block_id: int) -> List[Message]:
        """Получение сообщений для конкретного блока"""
        return [msg for msg in self._messages if msg.block_id == block_id]
    
    def has_errors(self) -> bool:
        """Проверка наличия ошибок"""
        return any(msg.type == MessageType.ERROR for msg in self._messages)
    
    def has_warnings(self) -> bool:
        """Проверка наличия предупреждений"""
        return any(msg.type == MessageType.WARNING for msg in self._messages)
    
    def count(self) -> int:
        """Общее количество сообщений"""
        return len(self._messages)
    
    def clear(self) -> None:
        """Очистка всех сообщений"""
        self._messages.clear()
    
    def to_list(self) -> List[dict]:
        """
        Преобразование в список словарей формата:
        [{blockId: num, type: "errors" | "warnings", text: }]
        """
        return [msg.to_dict() for msg in self._messages]
    
    def __len__(self) -> int:
        return len(self._messages)
    
    def __str__(self) -> str:
        if not self._messages:
            return "No messages"
        
        result = []
        for msg in self._messages:
            result.append(f"[{msg.type.value.upper()}] Block {msg.block_id}: {msg.text}")
        return "\n".join(result)


# Пример использования
if __name__ == "__main__":
    # Создаем коллектор сообщений
    collector = MessageCollector()
    
    # Добавляем ошибки и предупреждения
    collector.add_error(1, "Division by zero")
    collector.add_error(2, "File not found")
    collector.add_warning(1, "Variable might be undefined")
    collector.add_warning(3, "Deprecated function used")
    
    # Добавляем сообщение через классы
    error = Error(4, "Memory allocation failed")
    collector.add_message(error)
    
    # Получаем все сообщения в нужном формате
    messages_list = collector.to_list()
    print("Messages in required format:")
    for msg in messages_list:
        print(msg)
    
    # Проверяем наличие ошибок
    print(f"\nHas errors: {collector.has_errors()}")
    print(f"Has warnings: {collector.has_warnings()}")
    
    # Получаем статистику
    print(f"\nTotal messages: {collector.count()}")
    print(f"Errors count: {len(collector.get_errors())}")
    print(f"Warnings count: {len(collector.get_warnings())}")
    
    # Получаем сообщения для конкретного блока
    print(f"\nMessages for block 1:")
    for msg in collector.get_messages_by_block(1):
        print(f"  - {msg.type.value}: {msg.text}")
    
    # Выводим все сообщения в читаемом формате
    print(f"\nAll messages:\n{collector}")