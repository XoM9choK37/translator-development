from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

class TokenType(Enum):
    KEYWORD = "W"
    DELIMITER = "R"
    OPERATION = "O"
    IDENTIFIER = "I"
    NUMBER = "N"
    STRING = "S"
    COMMENT = "C"
    ERROR = "E"

@dataclass
class Token:
    code: str
    value: str
    line: int
    column: int
    lex_type: TokenType
    error_msg: str = ""

class OperatorPriority:
    """Таблица приоритетов операторов для алгоритма Дейкстры"""
    
    PRIORITIES = {
        # Приоритет 0 - открывающие скобки и специальные операторы
        'IF': 0,
        'WHILE': 0,
        '(': 0,
        '[': 0,
        '{': 0,
        'АЭМ': 0,
        'Ф': 0,
        
        # Приоритет 1 - закрывающие скобки и разделители
        ',': 1,
        ';': 1,
        ')': 1,
        ']': 1,
        '}': 1,
        'THEN': 1,
        'ELSE': 1,
        'DO': 1,
        
        # Приоритет 2 - присваивание
        ':=': 2,
        '=': 2,
        '<-': 2,
        
        # Приоритет 3 - логическое ИЛИ
        '|': 3,
        '||': 3,
        
        # Приоритет 4 - логическое И
        '&': 4,
        '&&': 4,
        
        # Приоритет 5 - отношения
        '<': 5,
        '>': 5,
        '<=': 5,
        '>=': 5,
        '==': 5,
        '!=': 5,
        
        # Приоритет 6 - сложение/вычитание
        '+': 6,
        '-': 6,
        
        # Приоритет 7 - умножение/деление
        '*': 7,
        '/': 7,
        '%%': 7,
        '%/%': 7,
        
        # Приоритет 8 - возведение в степень
        '^': 8,
        '**': 8,
        
        # Приоритет 9 - унарный минус
        'UMINUS': 9,
        
        # Приоритет 10 - метки
        ':': 10,
    }
    
    @classmethod
    def get_priority(cls, operator: str) -> int:
        return cls.PRIORITIES.get(operator, -1)
    
    @classmethod
    def is_operator(cls, token_value: str) -> bool:
        return token_value in cls.PRIORITIES

@dataclass
class StackItem:
    """Элемент стека"""
    value: str
    priority: int
    label: str = ""  # Для меток условных переходов
    counter: int = 1  # Счётчик операндов для функций и массивов

class RPNConverter:
    """Конвертер выражений в обратную польскую запись"""
    
    def __init__(self):
        self.stack: List[StackItem] = []
        self.output: List[str] = []
        self.label_counter = 0
        self.while_label_counter = 0
        self.errors: List[str] = []
        self.tokens: List[Token] = []
        
    def reset(self):
        """Сброс состояния конвертера"""
        self.stack = []
        self.output = []
        self.label_counter = 0
        self.while_label_counter = 0
        self.errors = []
        self.tokens = []
    
    def generate_label(self, prefix: str = "М") -> str:
        """Генерация уникальной метки"""
        if prefix == "МЦ":
            self.while_label_counter += 1
            return f"{prefix}{self.while_label_counter}"
        else:
            self.label_counter += 1
            return f"{prefix}{self.label_counter}"
    
    def get_token_priority(self, token: Token) -> int:
        """Получение приоритета токена"""
        if token.lex_type == TokenType.IDENTIFIER or token.lex_type == TokenType.NUMBER:
            return -1  # Операнды
        if token.lex_type == TokenType.KEYWORD:
            return OperatorPriority.get_priority(token.value.upper())
        if token.lex_type == TokenType.OPERATION:
            return OperatorPriority.get_priority(token.value)
        if token.lex_type == TokenType.DELIMITER:
            return OperatorPriority.get_priority(token.value)
        return -1
    
    def is_operand(self, token: Token) -> bool:
        """Проверка, является ли токен операндом"""
        return token.lex_type in [TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING]
    
    def is_operator(self, token: Token) -> bool:
        """Проверка, является ли токен оператором"""
        return (token.lex_type in [TokenType.OPERATION, TokenType.DELIMITER] or 
                (token.lex_type == TokenType.KEYWORD and 
                 token.value.upper() in ['IF', 'WHILE', 'THEN', 'ELSE', 'DO']))
    
    def pop_stack_to_output(self, until_priority: int = -1, until_value: str = None):
        """Выталкивание элементов из стека в выходную строку"""
        while self.stack:
            top = self.stack[-1]
            
            if until_value and top.value == until_value:
                self.stack.pop()
                break
            
            if until_priority >= 0 and top.priority < until_priority:
                break
            
            # Не выталкиваем WHILE, IF в выход напрямую
            if top.value in ['WHILE', 'IF', '(', '{']:
                break
            
            self.output.append(top.value)
            self.stack.pop()
    
    def process_token(self, token: Token):
        """Обработка одного токена"""
        # Пропускаем комментарии
        if token.lex_type == TokenType.COMMENT:
            return
        
        # Пропускаем ошибки
        if token.lex_type == TokenType.ERROR:
            self.errors.append(f"Ошибка в токене '{token.value}' на строке {token.line}")
            return
        
        # Операнды сразу в выход
        if self.is_operand(token):
            self.output.append(token.value)
            return
        
        # Обработка ключевых слов
        if token.lex_type == TokenType.KEYWORD:
            keyword = token.value.upper()
            
            if keyword == 'IF':
                # IF играет роль открывающей скобки с меткой
                label = self.generate_label("М")
                self.stack.append(StackItem(value='IF', priority=0, label=label))
                return
            
            elif keyword == 'WHILE':
                # WHILE - начало цикла с меткой начала
                label = self.generate_label("МЦ")
                self.stack.append(StackItem(value='WHILE', priority=0, label=label))
                return
            
            elif keyword == 'THEN':
                # THEN выталкивает до IF, добавляет условный переход
                self._process_then()
                return
            
            elif keyword == 'ELSE':
                # ELSE выталкивает до IF, добавляет безусловный переход
                self._process_else()
                return
            
            elif keyword == 'DO':
                # DO для while - в R не используется явно, обрабатывается через {
                self._process_do()
                return
        
        # Обработка операторов и разделителей
        if self.is_operator(token):
            self._process_operator(token)
            return
    
    def _process_then(self):
        """Обработка THEN в условном выражении"""
        # Выталкиваем все операции до IF
        while self.stack and self.stack[-1].value not in ['IF', 'WHILE']:
            top = self.stack.pop()
            self.output.append(top.value)
        
        if self.stack and self.stack[-1].value == 'IF':
            if_item = self.stack[-1]
            # Добавляем условный переход
            self.output.append(f"{if_item.label}")
            self.output.append("УПЛ")
            # Меняем метку для ELSE
            if_item.label = self.generate_label("М")
    
    def _process_else(self):
        """Обработка ELSE в условном выражении"""
        # Выталкиваем все операции до IF
        while self.stack and self.stack[-1].value not in ['IF', 'WHILE']:
            top = self.stack.pop()
            self.output.append(top.value)
        
        if self.stack and self.stack[-1].value == 'IF':
            if_item = self.stack[-1]
            # Добавляем безусловный переход
            new_label = self.generate_label("М")
            self.output.append(f"{new_label}")
            self.output.append("БП")
            self.output.append(f"{if_item.label}:")
            # Обновляем метку
            if_item.label = new_label
    
    def _process_do(self):
        """Обработка DO в цикле WHILE"""
        # Выталкиваем все операции до WHILE
        while self.stack and self.stack[-1].value != 'WHILE':
            top = self.stack.pop()
            self.output.append(top.value)
        
        if self.stack and self.stack[-1].value == 'WHILE':
            while_item = self.stack[-1]
            # Добавляем условный переход на конец цикла
            self.output.append(f"{while_item.label}")
            self.output.append("УПЛ")
    
    def _process_operator(self, token: Token):
        """Обработка оператора"""
        current_priority = self.get_token_priority(token)
        
        # Обработка закрывающей фигурной скобки (конец блока)
        if token.value == '}':
            self._process_closing_brace()
            return
        
        # Обработка закрывающей круглой скобки
        if token.value == ')':
            self.pop_stack_to_output(until_value='(')
            # Проверяем, не завершаем ли мы условное выражение
            if self.stack and self.stack[-1].value == 'IF':
                if_item = self.stack.pop()
                self.output.append(f"{if_item.label}:")
            return
        
        # Обработка открывающей скобки
        if token.value == '(':
            self.stack.append(StackItem(value='(', priority=0))
            return
        
        # Обработка открывающей фигурной скобки (начало блока)
        if token.value == '{':
            # Проверяем, не после ли WHILE идёт
            if self.stack and self.stack[-1].value == 'WHILE':
                # Это начало тела цикла WHILE
                self._process_while_body_start()
            self.stack.append(StackItem(value='{', priority=0))
            return
        
        # Обработка присваивания
        if token.value in ['=', '<-', ':=']:
            # Выталкиваем операции с более высоким приоритетом
            while self.stack:
                top = self.stack[-1]
                if top.priority >= current_priority and top.value not in ['WHILE', 'IF', '(', '{']:
                    self.output.append(top.value)
                    self.stack.pop()
                else:
                    break
            self.stack.append(StackItem(value=':=', priority=2))
            return
        
        # Стандартная обработка операторов
        while self.stack:
            top = self.stack[-1]
            
            if top.priority == 0:  # Открывающая скобка или IF/WHILE
                break
            
            if top.priority >= current_priority:
                self.output.append(top.value)
                self.stack.pop()
            else:
                break
        
        self.stack.append(StackItem(value=token.value, priority=current_priority))
    
    def _process_while_body_start(self):
        """Обработка начала тела цикла WHILE (после условия)"""
        # Выталкиваем условие из стека в выход
        while self.stack and self.stack[-1].value not in ['WHILE', 'IF']:
            top = self.stack.pop()
            self.output.append(top.value)
        
        if self.stack and self.stack[-1].value == 'WHILE':
            while_item = self.stack[-1]
            # Добавляем метку и условный переход
            self.output.append(f"{while_item.label}")
            self.output.append("УПЛ")
    
    def _process_closing_brace(self):
        """Обработка закрывающей фигурной скобки"""
        # Выталкиваем все операции до {
        while self.stack and self.stack[-1].value != '{':
            top = self.stack.pop()
            self.output.append(top.value)
        
        # Удаляем {
        if self.stack and self.stack[-1].value == '{':
            self.stack.pop()
        
        # Проверяем, не конец ли это цикла WHILE
        if self.stack and self.stack[-1].value == 'WHILE':
            while_item = self.stack.pop()
            # Добавляем метку возврата к началу цикла
            self.output.append(f"{while_item.label}:")
    
    def finalize(self):
        """Завершение конвертации - выталкивание остатка стека"""
        while self.stack:
            top = self.stack.pop()
            if top.value == 'WHILE':
                self.output.append(f"{top.label}:")
            elif top.value == 'IF':
                self.output.append(f"{top.label}:")
            elif top.value not in ['(', '{', ')', '}']:
                self.output.append(top.value)
    
    def convert(self, tokens: List[Token]) -> List[str]:
        """Основной метод конвертации"""
        self.reset()
        self.tokens = tokens
        
        for token in tokens:
            self.process_token(token)
        
        self.finalize()
        
        return self.output
    
    def get_stack_state(self) -> List[Dict]:
        """Получение текущего состояния стека"""
        return [
            {
                'value': item.value,
                'priority': item.priority,
                'label': item.label,
                'counter': item.counter
            }
            for item in self.stack
        ]
    
    def get_errors(self) -> List[str]:
        """Получение списка ошибок"""
        return self.errors