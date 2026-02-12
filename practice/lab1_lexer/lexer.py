import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import re
import datetime

class LexemType(Enum):
    KEYWORD = "W"      # служебные слова
    DELIMITER = "R"    # разделители
    OPERATION = "O"    # операции
    IDENTIFIER = "I"   # идентификаторы
    NUMBER = "N"       # числа
    STRING = "S"       # строки
    COMMENT = "C"      # комментарии
    ERROR = "E"        # ошибки

@dataclass
class Token:
    code: str
    value: str
    line: int
    column: int
    lex_type: LexemType
    error_msg: str = ""  # сообщение об ошибке для ошибочных токенов

class RLexer:
    def __init__(self):
        self.keywords = {}
        self.delimiters = {}
        self.operations = {}
        self.identifiers = {}
        self.numbers = {}
        self.strings = {}
        
        self.token_sequence = []
        self.errors = []
        self.error_tokens = []  # специальный список для ошибочных токенов
        
        self.current_line = 1
        self.current_column = 1
        
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц лексем R"""
        # Служебные слова R
        keywords_list = [
            "if", "else", "while", "for", "in", "next", "break",
            "function", "return", "TRUE", "FALSE", "NULL", "NA",
            "Inf", "NaN", "repeat", "switch", "try", "tryCatch",
            "stop", "warning", "require", "library", "source",
            "setwd", "getwd", "list", "matrix", "data.frame",
            "c", "cbind", "rbind", "length", "nrow", "ncol",
            "summary", "print", "cat", "paste", "sprintf",
            "subset", "merge", "apply", "lapply", "sapply",
            "tapply", "mapply", "aggregate", "plot", "ggplot",
            "lm", "glm", "summary.lm", "anova", "predict"
        ]
        
        for i, kw in enumerate(sorted(keywords_list), 1):
            self.keywords[kw] = i
        
        # Разделители
        delimiters_list = [
            ".", ",", ";", ":", "::", ":::",
            "(", ")", "[", "]", "[[", "]]",
            "{", "}", "'", "\"", "`", "$", "@",
            "\\", "\n", "\t", " ", "\r"
        ]
        
        for i, delim in enumerate(delimiters_list, 1):
            self.delimiters[delim] = i
        
        # Операции R
        operations_list = [
            "+", "-", "*", "/", "^", "**",
            "%%", "%/%", "%*%", "%in%",
            "<", ">", "<=", ">=", "==", "!=",
            "=", "<-", "<<-", "->", "->>",
            "&", "|", "!", "&&", "||",
            "~", ":", "$", "@",
            "%>%", "%T>%", "%<>%", "%$%"
        ]
        
        for i, op in enumerate(operations_list, 1):
            self.operations[op] = i
    
    def reset(self):
        """Сброс состояния анализатора"""
        self.identifiers = {}
        self.numbers = {}
        self.strings = {}
        self.token_sequence = []
        self.errors = []
        self.error_tokens = []
        self.current_line = 1
        self.current_column = 1
    
    def is_keyword(self, word):
        return self.keywords.get(word)
    
    def is_delimiter(self, char):
        return self.delimiters.get(char)
    
    def is_operation(self, op):
        return self.operations.get(op)
    
    def add_identifier(self, name):
        if name not in self.identifiers:
            self.identifiers[name] = len(self.identifiers) + 1
        return self.identifiers[name]
    
    def add_number(self, num):
        if num not in self.numbers:
            self.numbers[num] = len(self.numbers) + 1
        return self.numbers[num]
    
    def add_string(self, string):
        if string not in self.strings:
            self.strings[string] = len(self.strings) + 1
        return self.strings[string]
    
    def is_valid_number(self, num_str):
        """Проверка корректности числа"""
        # Пустая строка - не число
        if not num_str:
            return False, "Пустое число"
        
        # Проверка на множественные точки (1.2.3, 123.23.3)
        if num_str.count('.') > 1:
            return False, "Некорректное использование точки - число содержит несколько десятичных разделителей"
        
        # Проверка на буквы в числе (1a2a3, 123a, 45x67)
        has_valid_e = False
        for i, char in enumerate(num_str):
            if char.isalpha():
                # Проверка на допустимую экспоненту
                if char.lower() == 'e' and i > 0 and i < len(num_str) - 1:
                    # Проверяем, что после e идут цифры или знак +/-
                    next_char = num_str[i + 1]
                    if next_char.isdigit() or next_char in '+-':
                        has_valid_e = True
                        continue
                return False, f"Некорректное построение числа - содержит букву '{char}'"
        
        # Проверка на корректность экспоненциальной записи
        if 'e' in num_str.lower() or 'E' in num_str.lower():
            parts = re.split(r'[eE]', num_str)
            if len(parts) != 2:
                return False, "Некорректная экспоненциальная запись"
            if not parts[0] or not parts[1]:
                return False, "Некорректная экспоненциальная запись"
            
            # Проверка мантиссы
            mantissa = parts[0]
            if mantissa.count('.') > 1:
                return False, "Некорректная экспоненциальная запись - множественные точки в мантиссе"
            
            # Проверка экспоненты
            exponent = parts[1]
            if exponent and exponent[0] in '+-':
                exponent = exponent[1:]
            if not exponent or not exponent.isdigit():
                return False, "Некорректная экспоненциальная запись"
        
        return True, "Корректное число"
    
    def tokenize(self, code):
        """Основной метод лексического анализа с расширенной проверкой ошибок"""
        self.reset()
        
        i = 0
        length = len(code)
        
        while i < length:
            char = code[i]
            start_column = self.current_column
            
            # Пропуск пробелов
            if char.isspace():
                if char == '\n':
                    self.current_line += 1
                    self.current_column = 1
                else:
                    self.current_column += 1
                i += 1
                continue
            
            # Комментарии
            if char == '#':
                comment = ''
                start_line = self.current_line
                while i < length and code[i] != '\n':
                    comment += code[i]
                    i += 1
                    self.current_column += 1
                self.token_sequence.append(Token("C#", comment, start_line, start_column, LexemType.COMMENT))
                continue
            
            # Строки
            if char in ('"', "'"):
                quote = char
                string = char
                i += 1
                self.current_column += 1
                start_line = self.current_line
                
                while i < length and code[i] != quote:
                    if code[i] == '\\' and i + 1 < length:
                        string += code[i] + code[i + 1]
                        i += 2
                        self.current_column += 2
                    else:
                        string += code[i]
                        i += 1
                        self.current_column += 1
                
                if i < length and code[i] == quote:
                    string += quote
                    i += 1
                    self.current_column += 1
                    token_id = self.add_string(string)
                    self.token_sequence.append(Token(f"S{token_id}", string, start_line, start_column, LexemType.STRING))
                else:
                    error_msg = f"Незакрытая строка"
                    self.errors.append(f"Строка {start_line}, колонка {start_column}: {error_msg}")
                    self.token_sequence.append(Token("E1", string, start_line, start_column, LexemType.ERROR, error_msg))
                continue
            
            # Проверка на оператор диапазона ".."
            if char == '.' and i + 1 < length and code[i + 1] == '.':
                self.token_sequence.append(Token("R19", "..", self.current_line, start_column, LexemType.DELIMITER))
                i += 2
                self.current_column += 2
                continue
            
            # Идентификаторы и ключевые слова
            if char.isalpha() or char == '.' or char == '_':
                word = ''
                start_line = self.current_line
                start_col = self.current_column
                
                # Собираем слово
                while i < length and (code[i].isalnum() or code[i] in '._'):
                    word += code[i]
                    i += 1
                    self.current_column += 1
                
                # Проверка на ключевое слово
                kw_id = self.is_keyword(word)
                if kw_id:
                    self.token_sequence.append(Token(f"W{kw_id}", word, start_line, start_col, LexemType.KEYWORD))
                else:
                    token_id = self.add_identifier(word)
                    self.token_sequence.append(Token(f"I{token_id}", word, start_line, start_col, LexemType.IDENTIFIER))
                continue
            
            # Числа - ДЕТЕКТИРОВАНИЕ ВСЕХ ОШИБОК
            if char.isdigit() or (char == '.' and i + 1 < length and code[i + 1].isdigit()):
                number = ''
                start_line = self.current_line
                start_col = self.current_column
                
                # Собираем последовательность символов
                while i < length:
                    current_char = code[i]
                    
                    # Если встретили букву - это потенциальная ошибка
                    if current_char.isalpha():
                        # Проверяем, является ли это допустимой экспонентой
                        if current_char.lower() == 'e' and number and not number[-1].isalpha():
                            # Проверяем, что после e идут цифры или знак
                            if i + 1 < length and (code[i + 1].isdigit() or code[i + 1] in '+-'):
                                number += current_char
                                i += 1
                                self.current_column += 1
                                continue
                        
                        # Иначе - это ошибка: буква в числе
                        number += current_char
                        i += 1
                        self.current_column += 1
                        
                        # Продолжаем собирать оставшиеся символы
                        while i < length and (code[i].isalnum() or code[i] == '.'):
                            number += code[i]
                            i += 1
                            self.current_column += 1
                        
                        # Это ОШИБКА - число с буквами
                        error_msg = f"Некорректное построение числа - '{number}' содержит буквы"
                        self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg}")
                        self.token_sequence.append(Token("E3", number, start_line, start_col, LexemType.ERROR, error_msg))
                        break
                    
                    # Если встретили точку
                    elif current_char == '.':
                        # Проверяем, не является ли это оператором диапазона
                        if i + 1 < length and code[i + 1] == '.':
                            # Это оператор диапазона, не часть числа
                            break
                        
                        number += current_char
                        i += 1
                        self.current_column += 1
                        continue
                    
                    # Если встретили знак + или -
                    elif current_char in '+-':
                        # Проверяем, является ли это знаком экспоненты
                        if number and number[-1].lower() == 'e':
                            number += current_char
                            i += 1
                            self.current_column += 1
                            continue
                        else:
                            # Не часть числа
                            break
                    
                    # Если встретили цифру
                    elif current_char.isdigit():
                        number += current_char
                        i += 1
                        self.current_column += 1
                        continue
                    
                    # Любой другой символ - конец числа
                    else:
                        break
                
                # Если мы собрали число и не нашли ошибку
                if number and (not self.token_sequence or self.token_sequence[-1].lex_type != LexemType.ERROR):
                    is_valid, error_msg = self.is_valid_number(number)
                    if is_valid:
                        token_id = self.add_number(number)
                        self.token_sequence.append(Token(f"N{token_id}", number, start_line, start_col, LexemType.NUMBER))
                    else:
                        self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg} - '{number}'")
                        self.token_sequence.append(Token("E4", number, start_line, start_col, LexemType.ERROR, error_msg))
                continue
            
            # Операции и разделители
            op_found = False
            
            # Проверка на многосимвольные операции
            for length_op in range(4, 0, -1):
                if i + length_op <= length:
                    potential_op = code[i:i+length_op]
                    op_id = self.is_operation(potential_op)
                    if op_id:
                        self.token_sequence.append(Token(f"O{op_id}", potential_op, self.current_line, start_column, LexemType.OPERATION))
                        i += length_op
                        self.current_column += length_op
                        op_found = True
                        break
            
            if not op_found:
                # Разделители
                delim_id = self.is_delimiter(char)
                if delim_id:
                    self.token_sequence.append(Token(f"R{delim_id}", char, self.current_line, start_column, LexemType.DELIMITER))
                    i += 1
                    self.current_column += 1
                    continue
                
                # Односимвольные операции
                op_id = self.is_operation(char)
                if op_id:
                    self.token_sequence.append(Token(f"O{op_id}", char, self.current_line, start_column, LexemType.OPERATION))
                    i += 1
                    self.current_column += 1
                    continue
            
            if not op_found and not delim_id:
                error_msg = f"Неизвестный символ '{char}'"
                self.errors.append(f"Строка {self.current_line}, колонка {self.current_column}: {error_msg}")
                self.token_sequence.append(Token("E5", char, self.current_line, start_column, LexemType.ERROR, error_msg))
                i += 1
                self.current_column += 1
        
        return self.token_sequence

class RLexerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("R Lexical Analyzer - Лексический анализатор языка R")
        self.root.geometry("1400x800")
        
        # Установка иконки и темы
        self.root.configure(bg='#f0f0f0')
        
        self.lexer = RLexer()
        self.current_file = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть файл", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Сохранить результат", command=self.save_results, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        # Меню Анализ
        analyze_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Анализ", menu=analyze_menu)
        analyze_menu.add_command(label="Запустить анализ", command=self.analyze, accelerator="F5")
        analyze_menu.add_command(label="Очистить всё", command=self.clear_all)
        
        # Меню Примеры
        examples_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Примеры", menu=examples_menu)
        examples_menu.add_command(label="Корректный код R", command=self.load_correct_example)
        examples_menu.add_command(label="Ошибки в числах", command=self.load_number_errors_example)
        examples_menu.add_separator()
        examples_menu.add_command(label="Множественные точки", command=self.load_multiple_dots_example)
        examples_menu.add_command(label="Буквы в числах", command=self.load_letters_in_numbers_example)
        examples_menu.add_command(label="Корректные числа", command=self.load_correct_numbers_example)
        
        # Меню Просмотр
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Просмотр", menu=view_menu)
        view_menu.add_command(label="Полная последовательность лексем", command=self.show_full_sequence)
        
        # Меню Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Синтаксис R", command=self.show_r_syntax)
        help_menu.add_command(label="Типы ошибок", command=self.show_error_types)
        
        # Привязка горячих клавиш
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_results())
        self.root.bind('<F5>', lambda e: self.analyze())
        
        # Основной контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка весов для растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Верхняя панель с информацией
        info_frame = ttk.LabelFrame(main_frame, text="Информация", padding="5")
        info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)
        
        # Стандартные шрифты Ubuntu
        default_font = ('Ubuntu', 10)
        bold_font = ('Ubuntu', 10, 'bold')
        
        ttk.Label(info_frame, text="Файл:", font=default_font).grid(row=0, column=0, sticky=tk.W)
        self.file_label = ttk.Label(info_frame, text="Не выбран", foreground="gray", font=default_font)
        self.file_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(info_frame, text="Статус:", font=default_font).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.status_label = ttk.Label(info_frame, text="Готов к работе", foreground="green", font=bold_font)
        self.status_label.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Кнопка для просмотра полной последовательности
        ttk.Button(info_frame, text="Полная последовательность лексем", 
                  command=self.show_full_sequence).grid(row=0, column=4, padx=(50, 0))
        
        # Левая панель - исходный код
        left_frame = ttk.LabelFrame(main_frame, text="Исходный код на R", padding="5")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        # Стандартный шрифт для Ubuntu
        self.code_text = scrolledtext.ScrolledText(
            left_frame, 
            wrap=tk.WORD, 
            font=('Ubuntu', 11),
            background='#ffffff',
            foreground='#000000',
            insertbackground='black'
        )
        self.code_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка подсветки синтаксиса с Ubuntu шрифтами
        self.code_text.tag_configure("keyword", foreground="#0000ff", font=('Ubuntu', 11, 'bold'))
        self.code_text.tag_configure("string", foreground="#008000", font=('Ubuntu', 11))
        self.code_text.tag_configure("comment", foreground="#808080", font=('Ubuntu', 11, 'italic'))
        self.code_text.tag_configure("number", foreground="#ff8c00", font=('Ubuntu', 11, 'bold'))
        self.code_text.tag_configure("operation", foreground="#ff00ff", font=('Ubuntu', 11, 'bold'))
        self.code_text.tag_configure("error", foreground="#ff0000", background="#fff0f0", font=('Ubuntu', 11, 'bold'))
        
        # Кнопки управления
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, pady=10)
        
        ttk.Button(button_frame, text="Открыть файл", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Запустить анализ", command=self.analyze).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить", command=self.clear_code).pack(side=tk.LEFT, padx=5)
        
        # Правая панель с вкладками результатов
        right_frame = ttk.LabelFrame(main_frame, text="Результаты анализа", padding="5")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # Создание вкладок
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Вкладка с последовательностью лексем
        self.tokens_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tokens_frame, text="Лексемы")
        self.tokens_frame.columnconfigure(0, weight=1)
        self.tokens_frame.rowconfigure(0, weight=1)
        
        self.tokens_text = scrolledtext.ScrolledText(
            self.tokens_frame,
            wrap=tk.WORD,
            font=('Ubuntu', 10),
            background='#ffffff'
        )
        self.tokens_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Вкладка с таблицами
        self.tables_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tables_frame, text="Таблицы лексем")
        self.tables_frame.columnconfigure(0, weight=1)
        self.tables_frame.rowconfigure(0, weight=1)
        
        self.tables_text = scrolledtext.ScrolledText(
            self.tables_frame,
            wrap=tk.WORD,
            font=('Ubuntu', 10),
            background='#ffffff'
        )
        self.tables_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Вкладка с ошибками
        self.errors_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.errors_frame, text="Ошибки")
        self.errors_frame.columnconfigure(0, weight=1)
        self.errors_frame.rowconfigure(0, weight=1)
        
        self.errors_text = scrolledtext.ScrolledText(
            self.errors_frame,
            wrap=tk.WORD,
            font=('Ubuntu', 10),
            background='#fff0f0',
            foreground='#ff0000'
        )
        self.errors_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Вкладка с идентификаторами
        self.identifiers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.identifiers_frame, text="Идентификаторы")
        self.identifiers_frame.columnconfigure(0, weight=1)
        self.identifiers_frame.rowconfigure(0, weight=1)
        
        self.identifiers_tree = ttk.Treeview(
            self.identifiers_frame,
            columns=('ID', 'Имя'),
            show='headings',
            height=20
        )
        self.identifiers_tree.heading('ID', text='ID')
        self.identifiers_tree.heading('Имя', text='Имя')
        self.identifiers_tree.column('ID', width=100)
        self.identifiers_tree.column('Имя', width=300)
        
        scrollbar_id = ttk.Scrollbar(self.identifiers_frame, orient=tk.VERTICAL, command=self.identifiers_tree.yview)
        self.identifiers_tree.configure(yscrollcommand=scrollbar_id.set)
        
        self.identifiers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_id.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Вкладка с числами
        self.numbers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.numbers_frame, text="Числа")
        self.numbers_frame.columnconfigure(0, weight=1)
        self.numbers_frame.rowconfigure(0, weight=1)
        
        self.numbers_tree = ttk.Treeview(
            self.numbers_frame,
            columns=('ID', 'Значение', 'Тип', 'Статус'),
            show='headings',
            height=20
        )
        self.numbers_tree.heading('ID', text='ID')
        self.numbers_tree.heading('Значение', text='Значение')
        self.numbers_tree.heading('Тип', text='Тип')
        self.numbers_tree.heading('Статус', text='Статус')
        self.numbers_tree.column('ID', width=100)
        self.numbers_tree.column('Значение', width=150)
        self.numbers_tree.column('Тип', width=150)
        self.numbers_tree.column('Статус', width=200)
        
        scrollbar_num = ttk.Scrollbar(self.numbers_frame, orient=tk.VERTICAL, command=self.numbers_tree.yview)
        self.numbers_tree.configure(yscrollcommand=scrollbar_num.set)
        
        self.numbers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_num.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Нижняя панель статистики
        stats_frame = ttk.LabelFrame(main_frame, text="Статистика", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        stats_frame.columnconfigure(5, weight=1)
        
        self.stats_labels = {}
        stats_items = [
            ("Всего лексем:", "0", 0),
            ("Идентификаторов:", "0", 2),
            ("Чисел:", "0", 4),
            ("Строк:", "0", 6),
            ("Ключевых слов:", "0", 8),
            ("Операций:", "0", 10),
            ("Ошибок:", "0", 12)
        ]
        
        for i, (label, value, col) in enumerate(stats_items):
            ttk.Label(stats_frame, text=label, font=('Ubuntu', 10)).grid(row=0, column=col, sticky=tk.W, padx=(20 if i > 0 else 0, 0))
            self.stats_labels[label] = ttk.Label(stats_frame, text=value, foreground="blue", font=('Ubuntu', 10, 'bold'))
            self.stats_labels[label].grid(row=0, column=col + 1, sticky=tk.W, padx=(5, 20))
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(stats_frame, mode='indeterminate', length=200)
        self.progress.grid(row=0, column=14, padx=(50, 0))
        self.progress.grid_remove()
    
    def open_file(self):
        """Открытие файла с кодом R"""
        filename = filedialog.askopenfilename(
            title="Выберите файл с кодом R",
            filetypes=[("R files", "*.r"), ("R files", "*.R"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.code_text.delete(1.0, tk.END)
                self.code_text.insert(1.0, content)
                self.current_file = filename
                self.file_label.config(text=Path(filename).name, foreground="black")
                self.status_label.config(text="Файл загружен", foreground="green")
                
                # Подсветка синтаксиса
                self.highlight_syntax()
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{str(e)}")
    
    def load_correct_example(self):
        """Загрузка корректного примера кода R"""
        example_code = """# Пример корректного кода на R
calculate_stats <- function(data) {
    mean_val <- mean(data, na.rm = TRUE)
    sd_val <- sd(data, na.rm = TRUE)
    
    if (mean_val > 0) {
        result <- list(
            mean = mean_val,
            sd = sd_val,
            n = length(data)
        )
        return(result)
    } else {
        return(NULL)
    }
}

# Корректные числа
x <- 123.45
y <- 2.5e-3
z <- 100
w <- 1.6E-19
"""
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, example_code)
        self.highlight_syntax()
        self.current_file = None
        self.file_label.config(text="Пример: корректный код", foreground="green")
    
    def load_correct_numbers_example(self):
        """Загрузка примера с корректными числами"""
        example_code = """# Примеры КОРРЕКТНЫХ чисел в R

# 1. Целые числа
a <- 42
b <- 0
c <- 1000000
d <- -123

# 2. Числа с фиксированной точкой
e <- 123.45
f <- .5           # Корректно - начинается с точки
g <- 0.5
h <- -3.14
i <- 123.         # Корректно - заканчивается точкой

# 3. Числа с плавающей точкой (экспоненциальная запись)
j <- 2.5e-3      # Корректно - отрицательная экспонента
k <- 1.6E-19     # Корректно - с E
l <- 3e5         # Корректно - целая часть без точки
m <- .5e2        # Корректно - начинается с точки
n <- 123.e-4     # Корректно - заканчивается точкой

# 4. Разделители и операции
x <- c(1, 2, 3)   # Точка как разделитель
y <- list$element  # Точка как оператор доступа
z <- 1..2          # Две точки - оператор диапазона
"""
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, example_code)
        self.highlight_syntax()
        self.current_file = None
        self.file_label.config(text="Пример: корректные числа", foreground="green")
    
    def load_number_errors_example(self):
        """Загрузка примера с ошибками в числах"""
        example_code = """# Примеры НЕКОРРЕКТНЫХ чисел в R

# 1. Множественные точки (ЭТО ОШИБКИ)
a <- 123.23.3      # ОШИБКА: несколько десятичных разделителей
b <- 1.2.3.4       # ОШИБКА: множественные точки
c <- 123..45       # ОШИБКА: две точки подряд

# 2. Буквы в числах (ЭТО ОШИБКИ)
d <- 123a          # ОШИБКА: буква 'a' после цифр
e <- 123b213a      # ОШИБКА: буквы внутри числа
f <- 45x67         # ОШИБКА: буква 'x' внутри числа
g <- 1a2a3         # ОШИБКА: буквы 'a' между цифрами
h <- 1a2b3c        # ОШИБКА: множественные буквы

# 3. Некорректная экспоненциальная запись (ЭТО ОШИБКИ)
i <- 2.5e          # ОШИБКА: нет показателя степени
j <- 1.5e-         # ОШИБКА: нет показателя степени
k <- 3e2.5         # ОШИБКА: точка в экспоненте
l <- 4e2a          # ОШИБКА: буква в экспоненте

# 4. КОРРЕКТНЫЕ ЧИСЛА (для сравнения)
m <- 123.45        # КОРРЕКТНО: число с фиксированной точкой
n <- 2.5e-3        # КОРРЕКТНО: экспоненциальная запись
o <- 100           # КОРРЕКТНО: целое число
p <- .5            # КОРРЕКТНО: начинается с точки
q <- 123.          # КОРРЕКТНО: заканчивается точкой
"""
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, example_code)
        self.highlight_syntax()
        self.current_file = None
        self.file_label.config(text="Пример: ошибки в числах", foreground="orange")
    
    def load_multiple_dots_example(self):
        """Загрузка примера с множественными точками"""
        example_code = """# Примеры использования точки в R

# НЕКОРРЕКТНОЕ использование точки (ОШИБКИ)
price <- 123.23.3          # ОШИБКА! Две точки
version <- 1.2.3.4        # ОШИБКА! Три точки
value <- 123..45          # ОШИБКА! Две точки подряд
coord <- 12.34.56.78      # ОШИБКА! Множественные точки

# КОРРЕКТНОЕ использование точки
correct1 <- 123.45        # OK - одна точка (число)
correct2 <- .5            # OK - начинается с точки (число)
correct3 <- 123.          # OK - заканчивается точкой (число)
correct4 <- 2.5e-3        # OK - экспонента (число)

# Точка как разделитель и оператор
x <- list(a=1, b=2)      # OK - точка не часть числа
y <- x$a                  # OK - оператор доступа
z <- 1..2                 # OK - оператор диапазона (две точки)
"""
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, example_code)
        self.highlight_syntax()
        self.current_file = None
        self.file_label.config(text="Пример: использование точки", foreground="orange")
    
    def load_letters_in_numbers_example(self):
        """Загрузка примера с буквами в числах"""
        example_code = """# Примеры букв в числах

# НЕКОРРЕКТНЫЕ числа с буквами (ОШИБКИ)
a <- 123a                # ОШИБКА! 'a' не может быть в числе
b <- 45x                 # ОШИБКА! 'x' не может быть в числе
c <- 67y89              # ОШИБКА! Буква 'y' внутри числа
d <- 123b213a           # ОШИБКА! Множественные буквы
e <- 45x67y89           # ОШИБКА! Несколько букв
f <- 1a2a3              # ОШИБКА! Буквы 'a' между цифрами
g <- 1a2b3c             # ОШИБКА! Множественные буквы

# НЕКОРРЕКТНАЯ экспонента
h <- 2.5ea              # ОШИБКА! Буква 'a' после e
i <- 1.3e2b             # ОШИБКА! Буква 'b' в экспоненте

# КОРРЕКТНЫЕ числа
j <- 123               # OK - целое число
k <- 2.5e-3           # OK - экспонента с e
l <- 1.6E-19          # OK - экспонента с E
m <- 0.5              # OK - число с точкой

# КОРРЕКТНЫЕ идентификаторы (не числа)
var123 <- 10          # OK - идентификатор, начинается с буквы
x2 <- 20              # OK - идентификатор
test_a <- 30          # OK - идентификатор
"""
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, example_code)
        self.highlight_syntax()
        self.current_file = None
        self.file_label.config(text="Пример: буквы в числах", foreground="orange")
    
    def highlight_syntax(self):
        """Простая подсветка синтаксиса"""
        # Удаляем старые теги
        for tag in ["keyword", "string", "comment", "number", "operation", "error"]:
            self.code_text.tag_remove(tag, 1.0, tk.END)
        
        content = self.code_text.get(1.0, tk.END)
        
        # Подсветка комментариев
        for match in re.finditer(r'#.*$', content, re.MULTILINE):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.code_text.tag_add("comment", start, end)
        
        # Подсветка строк
        for match in re.finditer(r'"[^"\\]*(\\.[^"\\]*)*"|\'[^\'\\]*(\\.[^\'\\]*)*\'', content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.code_text.tag_add("string", start, end)
        
        # Подсветка ключевых слов
        for kw in self.lexer.keywords.keys():
            start = 1.0
            while True:
                start = self.code_text.search(r'\m' + re.escape(kw) + r'\M', start, tk.END)
                if not start:
                    break
                end = f"{start}+{len(kw)}c"
                self.code_text.tag_add("keyword", start, end)
                start = end
        
        # Подсветка ошибок - множественные точки и буквы в числах
        for match in re.finditer(r'\d*\.\d+\.\d+|\d+\.\d*\.\d*|\d+[a-zA-Z]+\d*|\d*[a-zA-Z]+\d+[a-zA-Z]*\d*', content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.code_text.tag_add("error", start, end)
    
    def highlight_errors(self):
        """Подсветка ошибочных конструкций в исходном коде"""
        # Удаляем старые подсветки ошибок
        self.code_text.tag_remove("error", 1.0, tk.END)
        
        # Подсвечиваем все найденные ошибки
        for token in self.lexer.token_sequence:
            if token.lex_type == LexemType.ERROR:
                start = f"{token.line}.0 + {token.column - 1} chars"
                end = f"{start} + {len(token.value)} chars"
                self.code_text.tag_add("error", start, end)
    
    def analyze(self):
        """Запуск лексического анализа"""
        code = self.code_text.get(1.0, tk.END)
        
        if not code.strip():
            messagebox.showwarning("Предупреждение", "Нет кода для анализа!")
            return
        
        # Показываем прогресс
        self.progress.grid()
        self.progress.start()
        self.status_label.config(text="Выполняется анализ...", foreground="orange")
        self.root.update()
        
        try:
            # Запускаем анализ
            tokens = self.lexer.tokenize(code)
            
            # Обновляем результаты
            self.update_results()
            
            # Обновляем статистику
            self.update_statistics()
            
            # Подсвечиваем ошибки в исходном коде
            self.highlight_errors()
            
            if self.lexer.errors:
                self.status_label.config(text=f"Анализ завершен. Найдено ошибок: {len(self.lexer.errors)}", foreground="red")
                # Переключаемся на вкладку с ошибками
                self.notebook.select(self.errors_frame)
            else:
                self.status_label.config(text="Анализ завершен. Ошибок не обнаружено", foreground="green")
            
        except Exception as e:
            self.status_label.config(text="Ошибка анализа", foreground="red")
            messagebox.showerror("Ошибка", f"Ошибка при анализе:\n{str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.progress.stop()
            self.progress.grid_remove()
    
    def show_full_sequence(self):
        """Отображение полной последовательности лексем в отдельном окне"""
        if not self.lexer.token_sequence:
            messagebox.showwarning("Предупреждение", "Нет данных для отображения! Сначала выполните анализ.")
            return
        
        # Создаем новое окно
        full_window = tk.Toplevel(self.root)
        full_window.title("Полная последовательность лексем")
        full_window.geometry("1000x600")
        full_window.configure(bg='#f0f0f0')
        
        # Основной фрейм
        main_frame = ttk.Frame(full_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        full_window.columnconfigure(0, weight=1)
        full_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="ПОЛНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ", 
                               font=('Ubuntu', 14, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Текстовое поле с прокруткой
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        full_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Ubuntu', 10),
            background='#ffffff'
        )
        full_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Формируем полную последовательность
        full_text.insert(1.0, "=" * 100 + "\n")
        full_text.insert(2.0, f"ПОЛНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ ({len(self.lexer.token_sequence)} шт.)\n")
        full_text.insert(3.0, "=" * 100 + "\n\n")
        
        # Группируем по строкам
        current_line = 1
        line_tokens = []
        
        for token in self.lexer.token_sequence:
            if token.line > current_line:
                # Выводим накопленные токены для предыдущей строки
                if line_tokens:
                    full_text.insert(tk.END, f"\n--- Строка {current_line} ---\n")
                    for i, t in enumerate(line_tokens, 1):
                        status = "ОШИБКА" if t.lex_type == LexemType.ERROR else "OK"
                        full_text.insert(tk.END, f"{i:4d}. {t.code:8s} | {t.value:25s} | позиция {t.column:4d} | {status}\n")
                        if t.error_msg:
                            full_text.insert(tk.END, f"      └─ {t.error_msg}\n")
                line_tokens = []
                current_line = token.line
            line_tokens.append(token)
        
        # Выводим последнюю строку
        if line_tokens:
            full_text.insert(tk.END, f"\n--- Строка {current_line} ---\n")
            for i, t in enumerate(line_tokens, 1):
                status = "ОШИБКА" if t.lex_type == LexemType.ERROR else "OK"
                full_text.insert(tk.END, f"{i:4d}. {t.code:8s} | {t.value:25s} | позиция {t.column:4d} | {status}\n")
                if t.error_msg:
                    full_text.insert(tk.END, f"      └─ {t.error_msg}\n")
        
        # Статистика
        full_text.insert(tk.END, "\n" + "=" * 100 + "\n")
        full_text.insert(tk.END, "СТАТИСТИКА ПО ЛЕКСЕМАМ\n")
        full_text.insert(tk.END, "=" * 100 + "\n")
        
        # Подсчет типов лексем
        type_counts = {}
        for token in self.lexer.token_sequence:
            type_name = {
                LexemType.KEYWORD: "Служебные слова",
                LexemType.IDENTIFIER: "Идентификаторы",
                LexemType.NUMBER: "Числа",
                LexemType.STRING: "Строки",
                LexemType.OPERATION: "Операции",
                LexemType.DELIMITER: "Разделители",
                LexemType.COMMENT: "Комментарии",
                LexemType.ERROR: "Ошибки"
            }.get(token.lex_type, token.lex_type.value)
            
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        for type_name, count in sorted(type_counts.items()):
            full_text.insert(tk.END, f"{type_name:20s}: {count:4d} лексем\n")
        
        # Кнопка закрытия
        ttk.Button(main_frame, text="Закрыть", command=full_window.destroy).grid(row=2, column=0, pady=10)
    
    def update_results(self):
        """Обновление всех результатов в интерфейсе"""
        
        # Последовательность лексем (первые 100)
        self.tokens_text.delete(1.0, tk.END)
        self.tokens_text.insert(1.0, "ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ (первые 100)\n")
        self.tokens_text.insert(2.0, "=" * 90 + "\n")
        self.tokens_text.insert(3.0, f"{'№':4s} {'Код':8s} {'Значение':25s} {'Строка':8s} {'Колонка':8s} {'Статус':15s}\n")
        self.tokens_text.insert(4.0, "-" * 90 + "\n")
        
        for i, token in enumerate(self.lexer.token_sequence[:100], 1):
            status = "ОШИБКА" if token.lex_type == LexemType.ERROR else "OK"
            line = f"{i:4d} {token.code:8s} {token.value:25s} {token.line:8d} {token.column:8d} {status:15s}\n"
            self.tokens_text.insert(tk.END, line)
            if token.error_msg:
                self.tokens_text.insert(tk.END, f"      └─ {token.error_msg}\n")
        
        if len(self.lexer.token_sequence) > 100:
            self.tokens_text.insert(tk.END, f"\n... и еще {len(self.lexer.token_sequence) - 100} лексем. ")
            self.tokens_text.insert(tk.END, "Используйте меню 'Просмотр > Полная последовательность лексем' для просмотра всех.\n")
        
        # Таблицы лексем
        self.tables_text.delete(1.0, tk.END)
        self.tables_text.insert(1.0, self.format_tables())
        
        # Ошибки
        self.errors_text.delete(1.0, tk.END)
        if self.lexer.errors:
            self.errors_text.insert(1.0, "=" * 80 + "\n")
            self.errors_text.insert(2.0, "НАЙДЕНЫ ОШИБКИ ЛЕКСИЧЕСКОГО АНАЛИЗА\n")
            self.errors_text.insert(3.0, "=" * 80 + "\n\n")
            
            # Группировка ошибок по типу
            dot_errors = [e for e in self.lexer.errors if "точк" in e.lower()]
            letter_errors = [e for e in self.lexer.errors if "букв" in e.lower()]
            other_errors = [e for e in self.lexer.errors if e not in dot_errors and e not in letter_errors]
            
            if dot_errors:
                self.errors_text.insert(tk.END, "📌 НЕКОРРЕКТНОЕ ИСПОЛЬЗОВАНИЕ ТОЧКИ:\n")
                self.errors_text.insert(tk.END, "-" * 40 + "\n")
                for i, error in enumerate(dot_errors, 1):
                    self.errors_text.insert(tk.END, f"{i}. {error}\n")
                self.errors_text.insert(tk.END, "\n")
            
            if letter_errors:
                self.errors_text.insert(tk.END, "📌 БУКВЫ В ЧИСЛАХ:\n")
                self.errors_text.insert(tk.END, "-" * 40 + "\n")
                for i, error in enumerate(letter_errors, 1):
                    self.errors_text.insert(tk.END, f"{i}. {error}\n")
                self.errors_text.insert(tk.END, "\n")
            
            if other_errors:
                self.errors_text.insert(tk.END, "📌 ПРОЧИЕ ОШИБКИ:\n")
                self.errors_text.insert(tk.END, "-" * 40 + "\n")
                for i, error in enumerate(other_errors, 1):
                    self.errors_text.insert(tk.END, f"{i}. {error}\n")
        else:
            self.errors_text.insert(1.0, "✅ Ошибок не обнаружено.\n")
        
        # Идентификаторы
        for item in self.identifiers_tree.get_children():
            self.identifiers_tree.delete(item)
        
        for name, idx in sorted(self.lexer.identifiers.items(), key=lambda x: x[1]):
            self.identifiers_tree.insert('', tk.END, values=(f"I{idx}", name))
        
        # Числа с классификацией и статусом
        for item in self.numbers_tree.get_children():
            self.numbers_tree.delete(item)
        
        for num, idx in sorted(self.lexer.numbers.items(), key=lambda x: x[1]):
            num_type = self.classify_number(num)
            self.numbers_tree.insert('', tk.END, values=(f"N{idx}", num, num_type, "Корректное"))
        
        # Добавляем ошибочные числа из токенов
        error_numbers = set()
        for token in self.lexer.token_sequence:
            if token.lex_type == LexemType.ERROR and any(c.isdigit() for c in token.value):
                if token.value not in error_numbers:
                    error_numbers.add(token.value)
                    if '.' in token.value:
                        if 'e' in token.value.lower():
                            num_type = "число с плавающей точкой"
                        else:
                            num_type = "число с фиксированной точкой"
                    else:
                        num_type = "целое число"
                    self.numbers_tree.insert('', tk.END, values=("E", token.value, num_type, f"ОШИБКА: {token.error_msg}"))
    
    def format_tables(self):
        """Форматирование таблиц лексем"""
        output = []
        
        output.append("=" * 80)
        output.append("ТАБЛИЦЫ ЛЕКСЕМ")
        output.append("=" * 80)
        
        # Служебные слова
        output.append("\n1. СЛУЖЕБНЫЕ СЛОВА:")
        output.append("-" * 40)
        for word, idx in sorted(self.lexer.keywords.items(), key=lambda x: x[1]):
            output.append(f"  W{idx:4d} : {word}")
        
        # Разделители
        output.append("\n2. РАЗДЕЛИТЕЛИ:")
        output.append("-" * 40)
        for delim, idx in sorted(self.lexer.delimiters.items(), key=lambda x: x[1]):
            repr_delim = repr(delim).strip("'")
            output.append(f"  R{idx:4d} : {repr_delim}")
        
        # Операции
        output.append("\n3. ОПЕРАЦИИ:")
        output.append("-" * 40)
        for op, idx in sorted(self.lexer.operations.items(), key=lambda x: x[1]):
            output.append(f"  O{idx:4d} : {op}")
        
        # Идентификаторы
        output.append("\n4. ИДЕНТИФИКАТОРЫ:")
        output.append("-" * 40)
        if self.lexer.identifiers:
            for name, idx in sorted(self.lexer.identifiers.items(), key=lambda x: x[1]):
                output.append(f"  I{idx:4d} : {name}")
        else:
            output.append("  Нет идентификаторов")
        
        # Числа
        output.append("\n5. ЧИСЛА:")
        output.append("-" * 40)
        if self.lexer.numbers:
            for num, idx in sorted(self.lexer.numbers.items(), key=lambda x: x[1]):
                num_type = self.classify_number(num)
                output.append(f"  N{idx:4d} : {num:15s} - {num_type}")
        else:
            output.append("  Нет чисел")
        
        # Строки
        output.append("\n6. СТРОКИ:")
        output.append("-" * 40)
        if self.lexer.strings:
            for string, idx in sorted(self.lexer.strings.items(), key=lambda x: x[1]):
                output.append(f"  S{idx:4d} : {string}")
        else:
            output.append("  Нет строк")
        
        # Статистика ошибок
        output.append("\n7. СТАТИСТИКА ОШИБОК:")
        output.append("-" * 40)
        output.append(f"  Всего ошибок: {len(self.lexer.errors)}")
        
        dot_errors = len([e for e in self.lexer.errors if "точк" in e.lower()])
        letter_errors = len([e for e in self.lexer.errors if "букв" in e.lower()])
        other_errors = len(self.lexer.errors) - dot_errors - letter_errors
        
        output.append(f"  - Некорректное использование точки: {dot_errors}")
        output.append(f"  - Буквы в числах: {letter_errors}")
        output.append(f"  - Прочие ошибки: {other_errors}")
        
        return '\n'.join(output)
    
    def classify_number(self, num_str):
        """Классификация чисел как в оригинальной программе"""
        if '.' in num_str:
            if 'e' in num_str.lower():
                return "число с плавающей точкой"
            else:
                return "число с фиксированной точкой"
        else:
            return "целое число"
    
    def update_statistics(self):
        """Обновление статистики"""
        error_count = len([t for t in self.lexer.token_sequence if t.lex_type == LexemType.ERROR])
        
        stats = {
            "Всего лексем:": len(self.lexer.token_sequence),
            "Идентификаторов:": len(self.lexer.identifiers),
            "Чисел:": len(self.lexer.numbers),
            "Строк:": len(self.lexer.strings),
            "Ключевых слов:": len([t for t in self.lexer.token_sequence if t.lex_type == LexemType.KEYWORD]),
            "Операций:": len([t for t in self.lexer.token_sequence if t.lex_type == LexemType.OPERATION]),
            "Ошибок:": error_count
        }
        
        for label, value in stats.items():
            if label in self.stats_labels:
                color = "red" if label == "Ошибок:" and value > 0 else "blue"
                self.stats_labels[label].config(text=str(value), foreground=color)
    
    def save_results(self):
        """Сохранение результатов анализа"""
        if not self.lexer.token_sequence:
            messagebox.showwarning("Предупреждение", "Нет результатов для сохранения!")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Сохранить результаты",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("РЕЗУЛЬТАТЫ ЛЕКСИЧЕСКОГО АНАЛИЗА\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(f"Дата анализа: {datetime.datetime.now()}\n")
                    f.write(f"Исходный файл: {self.current_file or 'Ввод с редактора'}\n\n")
                    
                    f.write("ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ:\n")
                    f.write("-" * 90 + "\n")
                    f.write(f"{'№':6s} {'Код':8s} {'Значение':25s} {'Строка':8s} {'Колонка':8s} {'Статус':15s}\n")
                    f.write("-" * 90 + "\n")
                    
                    for i, token in enumerate(self.lexer.token_sequence, 1):
                        status = "ОШИБКА" if token.lex_type == LexemType.ERROR else "OK"
                        f.write(f"{i:6d} | {token.code:8s} | {token.value:25s} | {token.line:8d} | {token.column:8d} | {status:15s}\n")
                        if token.error_msg:
                            f.write(f"      └─ {token.error_msg}\n")
                    
                    f.write("\n\n" + self.format_tables())
                
                messagebox.showinfo("Успех", f"Результаты сохранены в файл:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")
    
    def clear_code(self):
        """Очистка поля с кодом"""
        self.code_text.delete(1.0, tk.END)
        self.current_file = None
        self.file_label.config(text="Не выбран", foreground="gray")
    
    def clear_all(self):
        """Полная очистка всех полей"""
        self.clear_code()
        self.tokens_text.delete(1.0, tk.END)
        self.tables_text.delete(1.0, tk.END)
        self.errors_text.delete(1.0, tk.END)
        
        for item in self.identifiers_tree.get_children():
            self.identifiers_tree.delete(item)
        
        for item in self.numbers_tree.get_children():
            self.numbers_tree.delete(item)
        
        for label in self.stats_labels:
            self.stats_labels[label].config(text="0", foreground="blue")
        
        self.lexer.reset()
        self.status_label.config(text="Готов к работе", foreground="green")
    
    def show_about(self):
        """Информация о программе"""
        about_text = """
R Lexical Analyzer v2.2
Лексический анализатор для языка R

Разработано на Python с использованием Tkinter
В рамках курса по системному программированию

ВОЗМОЖНОСТИ:
• Полный лексический анализ языка R
• Отлавливание некорректных чисел с множественными точками (1.2.3)
• Отлавливание чисел с буквами (123a, 1a2a3, 123b213a)
• Поддержка корректных чисел: 2.5e-3, .5, 123., .5e2
• Подсветка ошибок в исходном коде
• Полная последовательность лексем в отдельном окне
• Детальная классификация ошибок
• Примеры для тестирования

© 2024
        """
        messagebox.showinfo("О программе", about_text)
    
    def show_r_syntax(self):
        """Справка по синтаксису R"""
        syntax_text = """
СИНТАКСИС ЯЗЫКА R

Ключевые слова:
if, else, while, for, function, return, TRUE, FALSE, NULL, NA, Inf, NaN

Операторы присваивания:
=, <-, <<-, ->, ->>, %

Арифметические операторы:
+, -, *, /, ^, %%, %/%

Логические операторы:
&, |, !, &&, ||, xor()

Операторы сравнения:
<, >, <=, >=, ==, !=

Специальные операторы:
%in%, %*%, %>% (magrittr pipe)

Комментарии:
# Однострочные комментарии

Строки:
'в одинарных кавычках' или "в двойных кавычках"

Разделители:
, ; : :: ::: ( ) [ ] [[ ]] { } $ @

ЧИСЛА В R:

✓ КОРРЕКТНЫЕ ЧИСЛА:
• Целые: 42, -123, 0
• С фикс. точкой: 3.14159, .5, 123.
• С плав. точкой: 2.5e-3, 1.6E-19, .5e2, 123.e-4

✗ НЕКОРРЕКТНЫЕ ЧИСЛА:
• Множественные точки: 123.23.3, 1.2.3.4
• Буквы в числах: 123a, 1a2a3, 45x67, 123b213a
• Некорректная экспонента: 2.5e, 1.5e-, 3e2.5, 4e2a

✓ ТОЧКА В R (не всегда число):
• Как десятичный разделитель: 123.45
• В начале числа: .5
• В конце числа: 123.
• Как оператор доступа: list$element
• Как оператор диапазона: 1..10
        """
        messagebox.showinfo("Синтаксис R", syntax_text)
    
    def show_error_types(self):
        """Справка по типам ошибок"""
        error_text = """
ТИПЫ ОШИБОК, ОТЛАВЛИВАЕМЫХ АНАЛИЗАТОРОМ:

1. НЕКОРРЕКТНОЕ ИСПОЛЬЗОВАНИЕ ТОЧКИ (E4):
   • Множественные точки: 123.23.3, 1.2.3.4, 12.34.56.78
   • Две точки подряд: 123..45 (НЕ путать с оператором диапазона 1..10!)
   • Точка в экспоненте: 1.5e2.3, 2.5e-3.4

2. БУКВЫ В ЧИСЛАХ (E3):
   • Буквы после цифр: 123a, 45x, 67y
   • Буквы внутри числа: 1a2a3, 123b213a, 45x67y89
   • Буквы в экспоненте: 2.5ea, 1.3e2b

3. НЕКОРРЕКТНОЕ ПОСТРОЕНИЕ ЧИСЛА (E2):
   • Начинается с цифры, содержит буквы: 123abc
   • Смешанный формат: 123a456

4. НЕЗАКРЫТЫЕ СТРОКИ (E1):
   • Отсутствует закрывающая кавычка

5. НЕИЗВЕСТНЫЕ СИМВОЛЫ (E5):
   • Символы, не принадлежащие алфавиту языка

❗ ЧТО НЕ ЯВЛЯЕТСЯ ОШИБКОЙ:
   • 2.5e-3 - корректная экспоненциальная запись
   • .5 - число, начинающееся с точки
   • 123. - число, заканчивающееся точкой
   • .5e2 - экспонента с числом, начинающимся с точки
   • 1..10 - оператор диапазона (две точки)

Программа подсвечивает ошибочные конструкции красным цветом
и предоставляет детальную статистику по типам ошибок.
        """
        messagebox.showinfo("Типы ошибок", error_text)

def main():
    root = tk.Tk()
    
    # Проверяем доступные шрифты и используем системный шрифт по умолчанию
    try:
        # Пробуем установить Ubuntu шрифт
        from tkinter import font
        available_fonts = font.families()
        if 'Ubuntu' in available_fonts:
            default_font = 'Ubuntu'
        elif 'DejaVu Sans' in available_fonts:
            default_font = 'DejaVu Sans'
        elif 'Liberation Sans' in available_fonts:
            default_font = 'Liberation Sans'
        else:
            default_font = 'TkDefaultFont'
    except:
        default_font = 'TkDefaultFont'
    
    app = RLexerGUI(root)
    
    # Загружаем пример с корректными числами для демонстрации
    app.load_correct_numbers_example()
    
    root.mainloop()

if __name__ == "__main__":
    main()
