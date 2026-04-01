import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os

from lexer import RLexer, LexemType, Token as LexerToken

from rpn_converter import RPNConverter, Token, TokenType

class RPNConverterGUI:
    """GUI приложение для конвертации R кода в ОПЗ"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Конвертер R в Обратную Польскую Запись")
        self.root.geometry("1600x900")
        
        self.lexer = RLexer()
        self.converter = RPNConverter()
        self.current_file = None
        
        self.setup_fonts()
        self.setup_ui()
        self.setup_menu()
        self.setup_bindings()
        
        # Загрузка примера
        self.load_example("while_example")
    
    def setup_fonts(self):
        """Настройка шрифтов"""
        from tkinter import font
        available_fonts = list(font.families())
        
        preferred_fonts = ['JetBrains Mono', 'Ubuntu', 'DejaVu Sans', 'Consolas', 'Arial']
        
        self.default_font = 'TkDefaultFont'
        for pref_font in preferred_fonts:
            if pref_font in available_fonts:
                self.default_font = pref_font
                break
        
        self.font_size = 14
        self.small_font_size = 12
        self.large_font_size = 16
        
        style = ttk.Style()
        style.configure('.', font=(self.default_font, self.font_size))
        style.configure('TLabel', font=(self.default_font, self.font_size))
        style.configure('TButton', font=(self.default_font, self.font_size))
        style.configure('Treeview', font=(self.default_font, self.small_font_size))
        style.configure('Treeview.Heading', font=(self.default_font, self.font_size, 'bold'))
    
    def setup_menu(self):
        """Настройка меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть файл", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Сохранить результат", command=self.save_results, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        # Анализ
        analyze_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Анализ", menu=analyze_menu)
        analyze_menu.add_command(label="Запустить конвертацию", command=self.convert_code, accelerator="F5")
        analyze_menu.add_command(label="Очистить всё", command=self.clear_all)
        
        # Примеры
        examples_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Примеры", menu=examples_menu)
        examples_menu.add_command(label="Простой пример", command=lambda: self.load_example("simple"))
        examples_menu.add_command(label="С циклом WHILE", command=lambda: self.load_example("while_example"))
        examples_menu.add_command(label="С IF-ELSE", command=lambda: self.load_example("if_else"))
        examples_menu.add_command(label="Сложный пример", command=lambda: self.load_example("complex"))
        
        # Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Правила ОПЗ", command=self.show_rpn_rules)
    
    def setup_bindings(self):
        """Настройка горячих клавиш"""
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_results())
        self.root.bind('<F5>', lambda e: self.convert_code())
    
    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Информация
        info_frame = ttk.LabelFrame(main_frame, text="Информация", padding="10")
        info_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        info_frame.columnconfigure(1, weight=1)
        
        ttk.Label(info_frame, text="Файл:", font=(self.default_font, self.font_size, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=5)
        self.file_label = ttk.Label(info_frame, text="Не выбран", foreground="gray")
        self.file_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(info_frame, text="Статус:", font=(self.default_font, self.font_size, 'bold')).grid(
            row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.status_label = ttk.Label(info_frame, text="Готов к работе", foreground="green", 
                                      font=(self.default_font, self.font_size, 'bold'))
        self.status_label.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Левая панель - Исходный код
        left_frame = ttk.LabelFrame(main_frame, text="Исходный код на R", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        self.code_text = scrolledtext.ScrolledText(
            left_frame,
            wrap=tk.NONE,
            font=(self.default_font, self.font_size),
            background='#ffffff',
            foreground='#000000'
        )
        self.code_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Контролы для кода
        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=1, column=0, pady=15)
        
        ttk.Button(control_frame, text="Открыть файл", command=self.open_file, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Конвертировать", command=self.convert_code, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Очистить", command=self.clear_code, width=15).pack(side=tk.LEFT, padx=5)
        
        # Центральная панель - Стек
        center_frame = ttk.LabelFrame(main_frame, text="Стек операций", padding="10")
        center_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        center_frame.columnconfigure(0, weight=1)
        center_frame.rowconfigure(0, weight=1)
        
        self.stack_tree = ttk.Treeview(
            center_frame,
            columns=('Значение', 'Приоритет', 'Метка'),
            show='headings',
            height=20
        )
        self.stack_tree.heading('Значение', text='Значение')
        self.stack_tree.heading('Приоритет', text='Приоритет')
        self.stack_tree.heading('Метка', text='Метка')
        
        self.stack_tree.column('Значение', width=120)
        self.stack_tree.column('Приоритет', width=80)
        self.stack_tree.column('Метка', width=120)
        
        scrollbar_stack = ttk.Scrollbar(center_frame, orient=tk.VERTICAL, command=self.stack_tree.yview)
        self.stack_tree.configure(yscrollcommand=scrollbar_stack.set)
        
        self.stack_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_stack.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Правая панель - Результат ОПЗ
        right_frame = ttk.LabelFrame(main_frame, text="Обратная польская запись", padding="10")
        right_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        self.rpn_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.font_size),
            background='#f0f8ff',
            foreground='#000080'
        )
        self.rpn_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Нижняя панель - Ошибки
        errors_frame = ttk.LabelFrame(main_frame, text="Ошибки", padding="10")
        errors_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(15, 0))
        errors_frame.columnconfigure(0, weight=1)
        errors_frame.rowconfigure(0, weight=1)
        
        self.errors_text = scrolledtext.ScrolledText(
            errors_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.small_font_size),
            background='#fff0f0',
            foreground='#ff0000',
            height=5
        )
        self.errors_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def load_example(self, example_type):
        """Загрузка примера кода"""
        examples = {
            "simple": """# Простой пример
x <- 5
y <- 10
z <- x + y * 2
""",
            "while_example": """# Пример с циклом WHILE
i <- 1
sum <- 0
while (i <= 10) {
    sum <- sum + i
    i <- i + 1
}
result <- sum
""",
            "if_else": """# Пример с IF-ELSE
x <- 15
if (x > 10) {
    y <- x * 2
} else {
    y <- x + 5
}
z <- y
""",
            "complex": """# Сложный пример
a <- 5
b <- 10
c <- 0
i <- 1

while (i <= a) {
    if (b > 5) {
        c <- c + i * 2
    } else {
        c <- c + i
    }
    i <- i + 1
}

result <- c / a
"""
        }
        
        if example_type in examples:
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, examples[example_type])
            self.current_file = None
            self.file_label.config(text=f"Пример: {example_type}", foreground="green")
    
    def open_file(self):
        """Открытие файла с кодом"""
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
                self.file_label.config(text=os.path.basename(filename), foreground="black")
                self.status_label.config(text="Файл загружен", foreground="green")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{str(e)}")
    
    def clear_code(self):
        """Очистка кода"""
        self.code_text.delete(1.0, tk.END)
        self.current_file = None
        self.file_label.config(text="Не выбран", foreground="gray")
    
    def clear_all(self):
        """Полная очистка"""
        self.clear_code()
        self.rpn_text.delete(1.0, tk.END)
        self.errors_text.delete(1.0, tk.END)
        
        for item in self.stack_tree.get_children():
            self.stack_tree.delete(item)
        
        self.lexer.reset()
        self.converter.reset()
        self.status_label.config(text="Готов к работе", foreground="green")
    
    def convert_code(self):
        """Конвертация кода в ОПЗ"""
        code = self.code_text.get(1.0, tk.END)
        
        if not code.strip():
            messagebox.showwarning("Предупреждение", "Нет кода для конвертации!")
            return
        
        self.status_label.config(text="Выполняется конвертация...", foreground="orange")
        self.root.update()
        
        try:
            # Лексический анализ
            tokens = self.lexer.tokenize(code)
            
            # Проверка на ошибки лексического анализа
            lexer_errors = [t for t in tokens if t.lex_type == LexemType.ERROR]
            if lexer_errors:
                self.errors_text.delete(1.0, tk.END)
                self.errors_text.insert(1.0, "ОШИБКИ ЛЕКСИЧЕСКОГО АНАЛИЗА:\n")
                self.errors_text.insert(tk.END, "=" * 60 + "\n")
                for error in lexer_errors:
                    self.errors_text.insert(tk.END, f"Строка {error.line}, колонка {error.column}: {error.error_msg}\n")
                self.status_label.config(text=f"Найдено ошибок: {len(lexer_errors)}", foreground="red")
                return
            
            # Конвертация в ОПЗ
            rpn_tokens = self._convert_tokens(tokens)
            rpn_output = self.converter.convert(rpn_tokens)
            
            # Отображение результата
            self._display_rpn(rpn_output)
            
            # Отображение стека
            self._display_stack()
            
            # Отображение ошибок конвертера
            converter_errors = self.converter.get_errors()
            if converter_errors:
                self.errors_text.delete(1.0, tk.END)
                self.errors_text.insert(1.0, "ОШИБКИ КОНВЕРТАЦИИ:\n")
                self.errors_text.insert(tk.END, "=" * 60 + "\n")
                for error in converter_errors:
                    self.errors_text.insert(tk.END, f"{error}\n")
                self.status_label.config(text=f"Конвертация завершена. Ошибок: {len(converter_errors)}", foreground="orange")
            else:
                self.errors_text.delete(1.0, tk.END)
                self.errors_text.insert(1.0, "✅ Ошибок не обнаружено\n")
                self.status_label.config(text="Конвертация завершена успешно", foreground="green")
            
        except Exception as e:
            self.status_label.config(text="Ошибка конвертации", foreground="red")
            messagebox.showerror("Ошибка", f"Ошибка при конвертации:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def _convert_tokens(self, lexer_tokens):
        """Преобразование токенов лексера в токены конвертера"""
        converted = []
        
        for lt in lexer_tokens:
            # Пропускаем комментарии
            if lt.lex_type == LexemType.COMMENT:
                continue
            
            # Определяем тип токена для конвертера
            if lt.lex_type == LexemType.KEYWORD:
                lex_type = TokenType.KEYWORD
            elif lt.lex_type == LexemType.IDENTIFIER:
                lex_type = TokenType.IDENTIFIER
            elif lt.lex_type == LexemType.NUMBER:
                lex_type = TokenType.NUMBER
            elif lt.lex_type == LexemType.STRING:
                lex_type = TokenType.STRING
            elif lt.lex_type == LexemType.OPERATION:
                lex_type = TokenType.OPERATION
            elif lt.lex_type == LexemType.DELIMITER:
                lex_type = TokenType.DELIMITER
            else:
                continue
            
            # Преобразуем значение для ключевых слов
            value = lt.value.strip()
            if lt.lex_type == LexemType.KEYWORD:
                value = value.upper()
            
            converted.append(Token(
                code=lt.code,
                value=value,
                line=lt.line,
                column=lt.column,
                lex_type=lex_type
            ))
        
        return converted
    
    def _display_rpn(self, rpn_output):
        """Отображение ОПЗ"""
        self.rpn_text.delete(1.0, tk.END)
        
        self.rpn_text.insert(1.0, "ОБРАТНАЯ ПОЛЬСКАЯ ЗАПИСЬ:\n")
        self.rpn_text.insert(tk.END, "=" * 60 + "\n\n")
        
        # Форматируем вывод
        line = ""
        for i, item in enumerate(rpn_output):
            if item.endswith(':'):
                line += f"\n{item} "
            elif item in ['УПЛ', 'БП']:
                line += f"{item} "
            else:
                line += f"{item} "
            
            # Перенос строки каждые 10 элементов
            if (i + 1) % 10 == 0:
                line += "\n"
        
        self.rpn_text.insert(tk.END, line)
        self.rpn_text.insert(tk.END, "\n\n" + "=" * 60 + "\n")
        self.rpn_text.insert(tk.END, f"Всего элементов: {len(rpn_output)}\n")
    
    def _display_stack(self):
        """Отображение состояния стека"""
        for item in self.stack_tree.get_children():
            self.stack_tree.delete(item)
        
        stack_state = self.converter.get_stack_state()
        
        # Отображаем в обратном порядке (верх стека сверху)
        for item in reversed(stack_state):
            self.stack_tree.insert('', 0, values=(
                item['value'],
                item['priority'],
                item['label']
            ))
    
    def save_results(self):
        """Сохранение результатов"""
        rpn_content = self.rpn_text.get(1.0, tk.END)
        
        if not rpn_content.strip():
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
                    f.write("РЕЗУЛЬТАТЫ КОНВЕРТАЦИИ В ОПЗ\n")
                    f.write("=" * 80 + "\n\n")
                    
                    if self.current_file:
                        f.write(f"Исходный файл: {self.current_file}\n\n")
                    
                    f.write("ИСХОДНЫЙ КОД:\n")
                    f.write("-" * 60 + "\n")
                    f.write(self.code_text.get(1.0, tk.END))
                    f.write("\n")
                    
                    f.write("ОБРАТНАЯ ПОЛЬСКАЯ ЗАПИСЬ:\n")
                    f.write("-" * 60 + "\n")
                    f.write(rpn_content)
                    
                    errors_content = self.errors_text.get(1.0, tk.END)
                    if errors_content.strip():
                        f.write("\nОШИБКИ:\n")
                        f.write("-" * 60 + "\n")
                        f.write(errors_content)
                
                messagebox.showinfo("Успех", f"Результаты сохранены в файл:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")
    
    def show_about(self):
        """О программе"""
        about_text = """КОНВЕРТЕР R В ОБРАТНУЮ ПОЛЬСКУЮ ЗАПИСЬ

Версия: 1.0
Год: 2026

Программа реализует алгоритм Дейкстры для перевода
выражений языка R в обратную польскую запись.

Особенности:
- Лексический анализ кода
- Построение ОПЗ с использованием стека
- Поддержка условных операторов (IF-THEN-ELSE)
- Поддержка циклов (WHILE)
- Визуализация состояния стека
- Сохранение результатов

На основе лабораторной работы №2
"Перевод исходной программы в обратную польскую запись"
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("О программе")
        help_window.geometry("600x500")
        help_window.configure(bg='#f0f0f0')
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, 
                                         font=(self.default_font, self.font_size))
        text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        text.insert(1.0, about_text)
        text.config(state=tk.DISABLED)
        
        ttk.Button(help_window, text="Закрыть", command=help_window.destroy).pack(pady=10)
    
    def show_rpn_rules(self):
        """Правила ОПЗ"""
        rules_text = """ПРАВИЛА ПЕРЕВОДА В ОБРАТНУЮ ПОЛЬСКУЮ ЗАПИСЬ

1. ОПЕРАНДЫ (переменные, числа):
   - Сразу записываются в выходную строку

2. ОПЕРАТОРЫ:
   - Сравнивается приоритет с верхним элементом стека
   - Если приоритет выше - оператор заносится в стек
   - Если приоритет ниже или равен - выталкивается из стека

3. СКОБКИ:
   - '(' - всегда заносится в стек
   - ')' - выталкивает все операторы до '('

4. УСЛОВНЫЕ ОПЕРАТОРЫ (IF-THEN-ELSE):
   - IF - заносится в стек с меткой
   - THEN - выталкивает до IF, добавляет "Метка УПЛ"
   - ELSE - выталкивает до IF, добавляет "Метка БП Метка:"
   - ')' - завершает условное выражение

5. ЦИКЛЫ (WHILE):
   - WHILE - заносится в стек с меткой начала цикла
   - DO - выталкивает до WHILE, добавляет "Метка УПЛ"
   - '}' - завершает цикл, добавляет "Метка:"

6. ПРИСВАИВАНИЕ:
   - Оператор ':=' записывается в конце выражения
   - Формат: <переменная> <выражение> :=

ПРИОРИТЕТЫ ОПЕРАТОРОВ (от высшего к низшему):
9  - Унарный минус
8  - Возведение в степень (^, **)
7  - Умножение, деление (*, /, %%, %/%)
6  - Сложение, вычитание (+, -)
5  - Отношения (<, >, <=, >=, ==, !=)
4  - Логическое И (&, &&)
3  - Логическое ИЛИ (|, ||)
2  - Присваивание (=, <-, :=)
1  - THEN, ELSE, DO, скобки закрывающие
0  - IF, WHILE, скобки открывающие
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Правила ОПЗ")
        help_window.geometry("800x700")
        help_window.configure(bg='#f0f0f0')
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, 
                                         font=(self.default_font, self.small_font_size))
        text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        text.insert(1.0, rules_text)
        text.config(state=tk.DISABLED)
        
        ttk.Button(help_window, text="Закрыть", command=help_window.destroy).pack(pady=10)


def main():
    root = tk.Tk()
    root.option_add('*Font', 'TkDefaultFont 14')
    app = RPNConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()