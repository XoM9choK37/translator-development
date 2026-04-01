import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pathlib import Path
import re
import datetime
from enum import Enum


class LexemType(Enum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    COMMENT = "COMMENT"
    OPERATION = "OPERATION"
    DELIMITER = "DELIMITER"
    ERROR = "ERROR"


class Token:
    def __init__(self, code, value, line, column, lex_type, error_msg=""):
        self.code = code
        self.value = value
        self.line = line
        self.column = column
        self.lex_type = lex_type
        self.error_msg = error_msg

    def __repr__(self):
        status = "ОК" if self.lex_type != LexemType.ERROR else "ОШИБКА"
        return f"{self.code:<8} {self.value:<25} {self.line:<8} {self.column:<8} {status:<15}"


class RLexer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.token_sequence = []
        self.keywords = {}
        self.identifiers = {}
        self.numbers = {}
        self.strings = {}
        self.comments = {}
        self.operations = {}
        self.delimiters = {}
        self.errors = []
        self.current_line = 1
        self.current_column = 1
        self.original_code = ""

    def add_keyword(self, value):
        if value not in self.keywords:
            self.keywords[value] = len(self.keywords) + 1
        return self.keywords[value]

    def add_identifier(self, value):
        if value not in self.identifiers:
            self.identifiers[value] = len(self.identifiers) + 1
        return self.identifiers[value]

    def add_number(self, value):
        if value not in self.numbers:
            self.numbers[value] = len(self.numbers) + 1
        return self.numbers[value]

    def add_string(self, value):
        if value not in self.strings:
            self.strings[value] = len(self.strings) + 1
        return self.strings[value]

    def add_comment(self, value):
        if value not in self.comments:
            self.comments[value] = len(self.comments) + 1
        return self.comments[value]

    def add_operation(self, value):
        if value not in self.operations:
            self.operations[value] = len(self.operations) + 1
        return self.operations[value]

    def add_delimiter(self, value):
        if value not in self.delimiters:
            self.delimiters[value] = len(self.delimiters) + 1
        return self.delimiters[value]

    def is_keyword(self, value):
        keywords = {
            'if', 'else', 'while', 'for', 'function', 'return',
            'TRUE', 'FALSE', 'NULL', 'NA', 'Inf', 'NaN'
        }
        return value in keywords

    def is_operation(self, value):
        operations = {
            '+', '-', '*', '/', '^', '**', '%%', '%/%', '!', '&', '|',
            '&&', '||', '<', '>', '<=', '>=', '==', '!=', '<-',
            '<<-', '=', '->', '->>', '~', '$', '@', ':', '::', ':::'
        }
        return value in operations

    def is_delimiter(self, value):
        delimiters = {'(', ')', '[', ']', '{', '}', ',', ';', '`'}
        return value in delimiters

    def is_valid_number(self, num_str):
        # Basic check for R number format
        pattern = r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$'
        if re.match(pattern, num_str):
            mantissa, *exp_parts = num_str.replace('e', 'E').split('E')
            if exp_parts:
                exponent = exp_parts[0]
                if exponent and exponent[0] in '+-':
                    exponent = exponent[1:]
                if not exponent or not exponent.isdigit():
                    return False, "Некорректная экспоненциальная запись"
            return True, "Корректное число"
        return False, "Некорректный формат числа"

    def tokenize(self, code):
        self.reset()
        self.original_code = code
        i = 0
        length = len(code)

        while i < length:
            char = code[i]
            start_column = self.current_column

            if char.isspace():
                if char == '\n':
                    self.current_line += 1
                    self.current_column = 1
                else:
                    self.current_column += 1
                i += 1
                continue

            if char == '#':
                start_line = self.current_line
                start_col = self.current_column
                comment = ""
                while i < length and code[i] != '\n':
                    comment += code[i]
                    i += 1
                    self.current_column += 1
                # Exclude the '#' character
                clean_comment = comment[1:]
                if clean_comment.strip():  # Only add non-empty comments
                    token_id = self.add_comment(clean_comment)
                    self.token_sequence.append(Token(f"C{token_id:04d}", clean_comment, start_line, start_col, LexemType.COMMENT))
                continue  # Handles newline increment inside loop

            if char in ['"', "'"]:
                quote = char
                start_line = self.current_line
                start_col = self.current_column
                string = ""
                i += 1  # Skip opening quote
                self.current_column += 1
                while i < length and code[i] != quote:
                    if code[i] == '\n':
                        error_msg = f"Незакрытая строка"
                        self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg} - '{string}'")
                        self.token_sequence.append(Token("E5", string, start_line, start_col, LexemType.ERROR, error_msg))
                        break
                    string += code[i]
                    i += 1
                    self.current_column += 1

                if i < length and code[i] == quote:
                    string += quote  # Include closing quote
                    i += 1
                    self.current_column += 1
                    token_id = self.add_string(string)
                    self.token_sequence.append(Token(f"S{token_id:04d}", string, start_line, start_col, LexemType.STRING))
                continue

            if char.isalpha() or char == '.':
                start_line = self.current_line
                start_col = self.current_column
                identifier = ""

                # Handle identifiers starting with a dot
                if char == '.':
                    identifier += code[i]
                    i += 1
                    self.current_column += 1
                    # Check if it's a number starting with a dot
                    if i < length and code[i].isdigit():
                        while i < length and (code[i].isdigit() or code[i] == '.'):
                            identifier += code[i]
                            i += 1
                            self.current_column += 1
                        is_valid, msg = self.is_valid_number(identifier)
                        if is_valid:
                             token_id = self.add_number(identifier)
                             self.token_sequence.append(Token(f"N{token_id:04d}", identifier, start_line, start_col, LexemType.NUMBER))
                        else:
                             error_msg = f"Некорректное построение числа - '{identifier}'"
                             self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg}")
                             self.token_sequence.append(Token("E2", identifier, start_line, start_col, LexemType.ERROR, error_msg))
                        continue
                    # Check if it's an operator like ...
                    elif i < length and code[i] == '.':
                        if i + 1 < length and code[i + 1] == '.':
                            identifier += '..'  # Consume ..
                            i += 2
                            self.current_column += 2
                            # Check if preceded by a number -> error
                            if i > len(identifier) and code[i - len(identifier) - 1].isdigit():
                                error_msg = f"Множественное использование точки"
                                self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg} - '{identifier}'")
                                self.token_sequence.append(Token("E3", identifier, start_line, start_col, LexemType.ERROR, error_msg))
                            else:
                                token_id = self.add_operation(identifier)
                                self.token_sequence.append(Token(f"O{token_id:04d}", identifier, start_line, start_col, LexemType.OPERATION))
                            continue
                        elif i + 2 < length and code[i + 1] == '.' and code[i + 2] == '.':
                             identifier += '...' # Consume ...
                             i += 3
                             self.current_column += 3
                             # Check if preceded by a number -> error
                             if i > len(identifier) and code[i - len(identifier) - 1].isdigit():
                                 error_msg = f"Множественное использование точки"
                                 self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg} - '{identifier}'")
                                 self.token_sequence.append(Token("E3", identifier, start_line, start_col, LexemType.ERROR, error_msg))
                             else:
                                 token_id = self.add_operation(identifier)
                                 self.token_sequence.append(Token(f"O{token_id:04d}", identifier, start_line, start_col, LexemType.OPERATION))
                             continue
                        else: # Just a double dot ..
                             # Check if preceded by a number -> error
                             if i > len(identifier) and code[i - len(identifier) - 1].isdigit():
                                 error_msg = f"Множественное использование точки"
                                 self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg} - '{identifier}'")
                                 self.token_sequence.append(Token("E3", identifier, start_line, start_col, LexemType.ERROR, error_msg))
                             else:
                                 token_id = self.add_operation(identifier)
                                 self.token_sequence.append(Token(f"O{token_id:04d}", identifier, start_line, start_col, LexemType.OPERATION))
                             continue
                    # If it's just a single dot followed by non-digit/non-dot, it's an identifier
                    # Check rest of potential identifier characters
                    while i < length and (code[i].isalnum() or code[i] == '_'):
                        identifier += code[i]
                        i += 1
                        self.current_column += 1

                else: # Starts with a letter
                    while i < length and (code[i].isalnum() or code[i] == '_' or code[i] == '.'):
                        identifier += code[i]
                        i += 1
                        self.current_column += 1

                # Check for keywords first
                if self.is_keyword(identifier):
                    token_id = self.add_keyword(identifier)
                    self.token_sequence.append(Token(f"K{token_id:04d}", identifier, start_line, start_col, LexemType.KEYWORD))
                # Then check for operations (like ., .., ...)
                elif self.is_operation(identifier):
                    token_id = self.add_operation(identifier)
                    self.token_sequence.append(Token(f"O{token_id:04d}", identifier, start_line, start_col, LexemType.OPERATION))
                else: # It's an identifier
                    token_id = self.add_identifier(identifier)
                    self.token_sequence.append(Token(f"I{token_id:04d}", identifier, start_line, start_col, LexemType.IDENTIFIER))
                continue

            if char.isdigit():
                start_line = self.current_line
                start_col = self.current_column
                number = ""
                while i < length and (code[i].isdigit() or code[i] == '.'):
                    number += code[i]
                    i += 1
                    self.current_column += 1

                # Check for exponential part
                if i < length and code[i].lower() == 'e':
                    number += code[i]
                    i += 1
                    self.current_column += 1
                    if i < length and code[i] in '+-':
                        number += code[i]
                        i += 1
                        self.current_column += 1
                    while i < length and code[i].isdigit():
                        number += code[i]
                        i += 1
                        self.current_column += 1

                # Check for letters after number construction
                while i < length and code[i].isalnum():
                    number += code[i]
                    i += 1
                    self.current_column += 1

                is_valid, msg = self.is_valid_number(number)
                if is_valid:
                    token_id = self.add_number(number)
                    self.token_sequence.append(Token(f"N{token_id:04d}", number, start_line, start_col, LexemType.NUMBER))
                else:
                    error_msg = f"Некорректное построение числа - '{number}' содержит буквы"
                    self.errors.append(f"Строка {start_line}, колонка {start_col}: {error_msg}")
                    self.token_sequence.append(Token("E2", number, start_line, start_col, LexemType.ERROR, error_msg))
                continue

            if self.is_delimiter(char):
                token_id = self.add_delimiter(char)
                self.token_sequence.append(Token(f"D{token_id:04d}", char, self.current_line, start_column, LexemType.DELIMITER))
                i += 1
                self.current_column += 1
                continue

            op_id = self.is_operation(char)
            if op_id:
                token_id = self.add_operation(char)
                self.token_sequence.append(Token(f"O{token_id:04d}", char, self.current_line, start_column, LexemType.OPERATION))
                i += 1
                self.current_column += 1
                continue

            # Handle potential multi-character operators (simplified check)
            # This is a basic check and might miss complex ones
            potential_op = char
            temp_i = i + 1
            temp_col = self.current_column + 1
            while temp_i < length and code[temp_i] in '<>+-/*=!~$@:&|%^':
                 potential_op += code[temp_i]
                 if self.is_operation(potential_op):
                     temp_i += 1
                     temp_col += 1
                 else:
                     break
            if len(potential_op) > 1 and self.is_operation(potential_op):
                 token_id = self.add_operation(potential_op)
                 self.token_sequence.append(Token(f"O{token_id:04d}", potential_op, self.current_line, start_column, LexemType.OPERATION))
                 i = temp_i
                 self.current_column = temp_col
                 continue


            # If none of the above, it's an unknown character
            error_msg = f"Неизвестный символ '{char}'"
            self.errors.append(f"Строка {self.current_line}, колонка {self.current_column}: {error_msg}")
            self.token_sequence.append(Token("E5", char, self.current_line, start_column, LexemType.ERROR, error_msg))
            i += 1
            self.current_column += 1

        return self.token_sequence

    def generate_lexeme_program(self):
        if not self.token_sequence:
            return "Нет данных для отображения. Сначала выполните анализ."
        lines = {}
        for token in self.token_sequence:
            if token.line not in lines:
                lines[token.line] = []
            lines[token.line].append(token)

        result_lines = []
        max_line = max(lines.keys()) if lines else 0
        for line_num in range(1, max_line + 1):
            if line_num in lines:
                line_tokens = lines[line_num]
                line_str = self.original_code.split('\n')[line_num - 1]
                new_line_str = line_str
                # Sort tokens in line by column in reverse order for replacement
                sorted_tokens = sorted(line_tokens, key=lambda t: t.column, reverse=True)
                for token in sorted_tokens:
                    start_pos = token.column - 1
                    end_pos = start_pos + len(token.value)
                    new_line_str = new_line_str[:start_pos] + f"<{token.code}>" + new_line_str[end_pos:]
                result_lines.append(new_line_str)
            else:
                result_lines.append("") # Handle empty lines if any gaps exist

        return '\n'.join(result_lines)

    def generate_clean_lexeme_program(self):
        if not self.token_sequence or not self.original_code:
            return " "
        code_lines = self.original_code.splitlines()
        token_lines = {}

        for token in self.token_sequence:
            line_num = token.line - 1
            if line_num >= len(code_lines): # Safety check
                continue
            if line_num not in token_lines:
                token_lines[line_num] = {}
            token_lines[line_num][token.column - 1] = f"<{token.code}>"

        result_lines = []
        for line_idx, line in enumerate(code_lines):
            if line_idx in token_lines:
                sorted_cols = sorted(token_lines[line_idx].keys(), reverse=True)
                new_line = line
                for col in sorted_cols:
                    token_code = token_lines[line_idx][col]
                    # Find the original token value based on position
                    original_token_value = None
                    for t in self.token_sequence:
                        if t.line - 1 == line_idx and t.column - 1 == col:
                            original_token_value = t.value
                            break
                    if original_token_value:
                         start_char = col
                         end_char = col + len(original_token_value)
                         new_line = new_line[:start_char] + token_code + new_line[end_char:]
                result_lines.append(new_line)
            else:
                result_lines.append(line)

        return '\n'.join(result_lines)

    def get_statistics(self):
        type_counts = {}
        for token in self.token_sequence:
            t_type = token.lex_type.name
            type_counts[t_type] = type_counts.get(t_type, 0) + 1
        return type_counts

    def get_summary(self):
        total_tokens = len(self.token_sequence)
        total_keywords = len(self.keywords)
        total_identifiers = len(self.identifiers)
        total_numbers = len(self.numbers)
        total_strings = len(self.strings)
        total_comments = len(self.comments)
        total_operations = len(self.operations)
        total_delimiters = len(self.delimiters)
        total_errors = len(self.errors)
        return {
            "total_tokens": total_tokens,
            "keywords": total_keywords,
            "identifiers": total_identifiers,
            "numbers": total_numbers,
            "strings": total_strings,
            "comments": total_comments,
            "operations": total_operations,
            "delimiters": total_delimiters,
            "errors": total_errors
        }

    def generate_full_sequence_report(self):
        lines = ["ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ\n"]
        lines.append("-" * 90 + "\n")
        lines.append(f"{'№':<6} {'Код':<8} {'Значение':<25} {'Строка':<8} {'Колонка':<8} {'Статус':<15}\n")
        lines.append("-" * 90 + "\n")
        for i, token in enumerate(self.token_sequence, 1):
            status = "ОШИБКА" if token.lex_type == LexemType.ERROR else "OK"
            lines.append(f"{i:<6} {token.code:<8} {token.value:<25} {token.line:<8} {token.column:<8} {status:<15}\n")
            if token.error_msg:
                lines.append(f"{'':<6} {'└─':<8} {token.error_msg}\n")
        return "".join(lines)

    def generate_tables_report(self):
        result = ["ТАБЛИЦЫ ЛЕКСЕМ\n"]
        result.append("=" * 90 + "\n")

        result.append("\nКлючевые слова:\n")
        for kw, idx in sorted(self.keywords.items(), key=lambda item: item[1]):
            result.append(f" K{idx:04d} : {kw}\n")

        result.append("\nИдентификаторы:\n")
        for idf, idx in sorted(self.identifiers.items(), key=lambda item: item[1]):
            result.append(f" I{idx:04d} : {idf}\n")

        result.append("\nЧисла:\n")
        for num, idx in sorted(self.numbers.items(), key=lambda item: item[1]):
            result.append(f" N{idx:04d} : {num}\n")

        result.append("\nСтроки:\n")
        for s, idx in sorted(self.strings.items(), key=lambda item: item[1]):
            result.append(f" S{idx:04d} : {s}\n")

        result.append("\nКомментарии:\n")
        for comment, idx in sorted(self.comments.items(), key=lambda item: item[1]):
            result.append(f" C{idx:04d} : {comment}\n")

        result.append("\nОперации:\n")
        for op, idx in sorted(self.operations.items(), key=lambda item: item[1]):
            result.append(f" O{idx:04d} : {op}\n")

        result.append("\nРазделители:\n")
        for delim, idx in sorted(self.delimiters.items(), key=lambda item: item[1]):
            result.append(f" D{idx:04d} : {delim}\n")

        if self.errors:  # ✅ ИСПРАВЛЕНО: проверка на непустой список
            result.append("\nОшибки:\n")
            for err in self.errors:
                result.append(f" {err}\n")

        if len(self.keywords) > 10 or len(self.identifiers) > 10 or len(self.numbers) > 10 or len(self.strings) > 10 or len(self.comments) > 10 or len(self.operations) > 10 or len(self.delimiters) > 10:
            result.append("\n... и другие (см. полные таблицы)\n")

        return "".join(result)


# --- Новые классы для ОПЗ ---

class OPZLexemType(Enum):
    OPERAND = "OPERAND"
    OPERATION = "OPERATION"
    KEYWORD = "KEYWORD"
    CONTROL_FLOW = "CONTROL_FLOW" # IF, WHILE, THEN, ELSE, DO, etc.
    DELIMITER = "DELIMITER"      # (, ), [, ], ;


class OPZToken:
    def __init__(self, value, lex_type, line=0, column=0):
        self.value = value
        self.lex_type = lex_type
        self.line = line
        self.column = column

    def __repr__(self):
        return f"OPZToken({self.value}, {self.lex_type}, {self.line}, {self.column})"


class OPZTranslator:
    """
    Implements the Shunting Yard algorithm (Dijkstra's algorithm) to convert R code tokens
    into Reverse Polish Notation (OPZ), handling control flow like if/else and while.
    """
    def __init__(self):
        self.input_tokens = []
        self.stack = [] # Stack for operators and control flow keywords
        self.output = [] # Output queue for OPZ
        self.current_index = 0 # Index of the next token to process in input_tokens
        self.temp_counter = 0 # Counter for generating temporary labels
        self.labels = {} # Map for tracking generated labels (e.g., M1, MC1)
        self.errors = []
        self.label_counters = {'M': 0, 'MC': 0} # Separate counters for different label types

        # Define priorities based on the provided document and adapted for R
        # Lower number means higher precedence for stack operations
        # Priority 0: Keywords like IF, WHILE, (, [, FUNCTION
        # Priority 1: THEN, ELSE, DO, ), ], ;
        # Priority 2: Assignment := (using <-, =), GOTO (not needed here)
        # Priority 3: OR (V)
        # Priority 4: AND (&)
        # Priority 5: Relations: <, <=, >, >=, ==, !=
        # Priority 6: Add/Sub: +, -
        # Priority 7: Mul/Div: *, /
        # Priority 8: Power: ^
        # Priority 9: Others (lowest priority for this simplified version)
        # We add pseudo-tokens like IF_END, WHILE_START, WHILE_END for state management
        # Table 2.4 from the PDF:
        # IF ( [ AEM     -> 0
        # , ) ] THEN ELSE -> 1
        # V               -> 2
        # &               -> 3
        # ¬               -> 4
        # Relations       -> 5
        # + -             -> 6
        # * /             -> 7
        # Power           -> 8
        # We adapt this for R:
        # IF, WHILE act like '('
        # THEN, ELSE act like ','
        # Assignment <- acts like :=
        # ';', ')' act like ')'
        self.priorities = {
            # Keywords and Control Flow Starters (Priority 0)
            'IF': 0, 'WHILE': 0, # Act like '('
            '(': 0, '[': 0, # Function calls, indexing
            # Delimiters and Control Flow Enders/Connectors (Priority 1)
            'THEN': 1, 'ELSE': 1, 'DO': 1, # Act like ','
            ')': 1, ']': 1, ';': 1, # Act like ')'
            # Assignment (Priority 2) - acts like :=
            '<-': 2, '=': 2,
            # Logical operators
            '|': 3, # OR (V in doc)
            '&': 4, # AND (& in doc)
            # Relations (Priority 5)
            '<': 5, '<=': 5, '>': 5, '>=': 5, '==': 5, '!=': 5,
            # Add/Sub (Priority 6)
            '+': 6, '-': 6,
            # Mul/Div (Priority 7)
            '*': 7, '/': 7,
            # Power (Priority 8)
            '^': 8,
            # Internal markers (higher numbers, lower priority)
            'IF_END': 9, 'THEN_PART': 9, 'ELSE_PART': 9,
            'WHILE_START': 9, 'WHILE_END': 9,
        }

    def get_priority(self, token_value_or_tuple):
        # Return priority, default to 9 for unknown tokens (operands have no priority here)
        # Handle tuples by extracting the first element (the marker name)
        if isinstance(token_value_or_tuple, tuple):
            return self.priorities.get(token_value_or_tuple[0].upper(), 9)
        else:
            return self.priorities.get(token_value_or_tuple.upper(), 9)

    def reset(self):
        self.input_tokens = []
        self.stack = []
        self.output = []
        self.current_index = 0
        self.temp_counter = 0
        self.labels = {}
        self.errors = []
        self.label_counters = {'M': 0, 'MC': 0}

    def tokenize_input(self, code_string):
        """Simple tokenizer for demonstration. Uses existing lexer if available."""
        # This is a very basic tokenizer for demo purposes.
        # In practice, it should use the output from your RLexer.
        # For now, we'll split by spaces and common delimiters.
        # A real implementation would require a more robust approach.
        # Let's try a slightly better regex to separate words and operators
        # This regex splits on whitespace and common delimiters/operators
        # but keeps the delimiters as separate tokens.
        pattern = r'(\b\w+\b|[();,+\-*/<>=!&|^]|<-)'
        tokens = re.findall(pattern, code_string)
        opz_tokens = []
        line_num = 1
        col_num = 1
        for token_str in tokens:
             # Determine type based on simple checks
             upper_token = token_str.upper()
             if upper_token in ['IF', 'ELSE', 'WHILE', 'DO', 'THEN']:
                 lex_type = OPZLexemType.CONTROL_FLOW
             elif token_str in ['<-', '=', '+', '-', '*', '/', '^', '<', '<=', '>', '>=', '==', '!=', '&', '|']:
                 lex_type = OPZLexemType.OPERATION
             elif token_str in ['(', ')', '[', ']', '{', '}', ';']:
                 lex_type = OPZLexemType.DELIMITER
             else:
                 lex_type = OPZLexemType.OPERAND # Assume identifier or number

             opz_tokens.append(OPZToken(token_str, lex_type, line_num, col_num))
             col_num += len(token_str) + 1 # Approximate column position

        self.input_tokens = opz_tokens

    def get_next_label(self, prefix="M"):
        """Generates unique labels like M1, M2, MC1, MC2 etc."""
        self.label_counters[prefix] += 1
        return f"{prefix}{self.label_counters[prefix]}"

    def translate_step(self):
        """
        Performs one step of the translation algorithm.
        Returns True if there are more steps, False if finished or error occurred.
        """
        if self.errors:
             return False # Stop if an error already occurred

        if self.current_index >= len(self.input_tokens):
            # No more input tokens, flush the stack
            while self.stack:
                top_op = self.stack.pop()
                if top_op in ['(', ')', '[', ']', '{', '}', ';']: # Delimiters should not remain
                     self.errors.append(f"Mismatched delimiter found on stack: {top_op}")
                     return False
                # Handle pending control flow markers
                if isinstance(top_op, tuple):
                    marker_type, *marker_data = top_op
                    if marker_type == 'WHILE_END':
                        # Resolve WHILE loop: MC1 (condition check) ... body ... БП MC1 MC2:
                        _, end_label, start_label = top_op
                        self.output.append(start_label) # Jump back to condition check
                        self.output.append("БП")
                        self.output.append(end_label + ":") # Label for loop exit
                    elif marker_type == 'ELSE_PART':
                        # Resolve IF-ELSE block: M1 (after THEN) ... ELSE part ... M2 БП M1: ... M2:
                        _, skip_label = top_op
                        self.output.append(skip_label + ":") # Label after the entire IF-ELSE block
                    elif marker_type == 'THEN_END':
                        # Resolve IF without ELSE: M1 (after THEN) ... (no ELSE) ... M1:
                        _, label_after_then = top_op
                        self.output.append(label_after_then + ":") # Place label after THEN block
                    else:
                        # Handle unknown tuple marker
                        self.errors.append(f"Unknown marker on stack during flush: {top_op}")
                        return False
                else:
                    # Handle regular operators/keywords left on stack
                    self.output.append(top_op)
            return False # Finished successfully

        token = self.input_tokens[self.current_index]
        self.current_index += 1

        if token.lex_type in [OPZLexemType.OPERAND]:
            # If operand, push to output
            self.output.append(token.value)
        elif token.lex_type == OPZLexemType.CONTROL_FLOW:
            if token.value.upper() == 'IF':
                # IF acts like an opening bracket. Push to stack.
                # Generate a label for the jump after the THEN part (if condition is false).
                label_after_then = self.get_next_label("M")
                self.stack.append(('IF_THEN', label_after_then))
                # The jump (M УПЛ) will be placed after the condition and before the THEN block's actions.
            elif token.value.upper() == 'WHILE':
                # WHILE acts like an opening bracket.
                # Generate a label for the start of the condition check.
                label_condition = self.get_next_label("MC") # MC - Metka Cikla (Loop Label)
                self.output.append(label_condition) # Place label before condition
                self.stack.append(('WHILE_START', label_condition))
                # The loop body will execute after the condition.
                # At the end of the body (or when DO is processed further), we'll add the exit jump.
            elif token.value.upper() == 'THEN':
                 # Pop IF_THEN marker, check stack integrity
                 if not self.stack or not isinstance(self.stack[-1], tuple) or self.stack[-1][0] != 'IF_THEN':
                      self.errors.append("Missing 'IF' before 'THEN' or mismatched structure")
                      return False
                 # Get the label for the jump target (end of THEN block if condition is false)
                 _, label_after_then = self.stack.pop()
                 # Output the conditional jump (УПЛ) after the condition expression.
                 # This jump skips the THEN block if the condition is false.
                 self.output.append(label_after_then)
                 self.output.append("УПЛ")
                 # Push marker indicating we are now in the THEN part and where its execution might end.
                 # This marker will be used when ELSE is encountered or when the IF block finishes implicitly.
                 self.stack.append(('THEN_END', label_after_then))
            elif token.value.upper() == 'ELSE':
                 # Pop THEN_END marker, check stack integrity
                 if not self.stack or not isinstance(self.stack[-1], tuple) or self.stack[-1][0] != 'THEN_END':
                      self.errors.append("Missing 'THEN' before 'ELSE' or mismatched structure")
                      return False
                 # Get the label that was the target of the 'THEN' condition's jump (УПЛ).
                 # This is where execution continues if the IF condition was FALSE.
                 _, label_after_then = self.stack.pop()
                 # Generate a new label for the end of the entire IF-ELSE block.
                 label_if_else_end = self.get_next_label("M")
                 # Output an unconditional jump (БП) after the THEN block executes.
                 # This jump skips the ELSE block.
                 self.output.append(label_if_else_end)
                 self.output.append("БП")
                 # Place the label 'label_after_then' here. This is the target of the 'IF' condition's jump.
                 # If the IF condition was false, execution jumps here, which is the start of the ELSE block.
                 self.output.append(label_after_then + ":")
                 # Push marker for the ELSE part, including the label for the final end of the IF block.
                 self.stack.append(('ELSE_END', label_if_else_end))
            elif token.value.upper() == 'DO':
                 # Pop WHILE_START marker, check stack integrity
                 if not self.stack or not isinstance(self.stack[-1], tuple) or self.stack[-1][0] != 'WHILE_START':
                      self.errors.append("Missing 'WHILE' before 'DO'")
                      return False
                 # Pop the WHILE_START marker to get the loop start label
                 _, loop_start_label = self.stack.pop()
                 # Generate label for the end of the loop (exit target)
                 label_while_end = self.get_next_label("MC") # MC2 - Metka Cikla Exit
                 # Output the conditional jump (УПЛ) after the condition evaluation.
                 # This jump exits the loop if the condition is FALSE.
                 self.output.append(label_while_end)
                 self.output.append("УПЛ")
                 # Push WHILE_END marker with exit label and start label (for the back jump)
                 # This marker will be resolved when the loop body ends (when stack is flushed or next stmt).
                 self.stack.append(('WHILE_END', label_while_end, loop_start_label))


        elif token.value == ')':
             # Flush operators from stack until '(' is found
             flushed_ops = []
             while self.stack and self.stack[-1] != '(':
                 op = self.stack.pop()
                 if isinstance(op, tuple):
                      self.errors.append(f"Unexpected control flow marker '{op}' on stack during ')' processing.")
                      return False
                 flushed_ops.append(op)
             if not self.stack:
                  self.errors.append("Mismatched parentheses: missing '('")
                  return False
             self.stack.pop() # Pop the '(' delimiter itself
             # Add the flushed operators to the output
             self.output.extend(flushed_ops)
        elif token.value == ']':
             # Handle array indexing end - pop elements until [ is found
             # For simplicity in this basic version, assume [ was handled when operand was pushed
             # Real logic might involve an INDEXING operator
             pass # Placeholder for index handling
        elif token.lex_type == OPZLexemType.OPERATION or token.value in ['(', '[']:
             # Handle operators and opening delimiters
             current_op = token.value
             current_prec = self.get_priority(current_op)

             # Pop operators from stack to output based on precedence
             flushed_ops = []
             while (self.stack and
                    self.stack[-1] not in ['(', '['] and # Don't pop opening delimiters yet
                    self.get_priority(self.stack[-1]) >= current_prec): # Fixed: call get_priority on stack element
                 op_from_stack = self.stack.pop()
                 if isinstance(op_from_stack, tuple):
                      self.errors.append(f"Unexpected control flow marker '{op_from_stack}' on stack during operator processing.")
                      return False
                 flushed_ops.append(op_from_stack)

             # Add the flushed operators to output
             self.output.extend(flushed_ops)
             # Push the current operator/delimiter onto the stack
             self.stack.append(current_op)

        elif token.value == ';':
             # Semicolon acts as a statement separator, flush operators up to control flow or start of stack
             # This helps finalize parts of expressions/statements.
             flushed_ops = []
             while self.stack and self.stack[-1] not in ['IF', 'THEN_PART', 'ELSE_PART'] and not isinstance(self.stack[-1], tuple):
                 op = self.stack.pop()
                 if op in ['(', '[', ')', ']']: # Mismatched delimiter found during flush
                      self.errors.append(f"Mismatched delimiter found on stack during ';' processing: {op}")
                      return False
                 flushed_ops.append(op)
             # Add flushed operators to output
             self.output.extend(flushed_ops)
             # Do NOT pop control flow markers like IF_THEN, THEN_END, ELSE_END, WHILE_START, WHILE_END here.
             # They are resolved by specific keywords (ELSE, DO) or at the end of input.


        # After processing the token, check the top of the stack for resolved control flow markers
        # This resolves markers like ELSE_END or THEN_END when appropriate conditions are met
        # (e.g., when a new statement starts or input ends, implying the current block finished).
        # For this step-by-step simulator, we assume that when a new independent statement/token comes,
        # previous blocks might need finalization if they were waiting for it implicitly (e.g., IF without ELSE).
        # However, the most reliable place for finalization is often during the stack flush at the end.
        # Let's handle finalization here by checking if the top marker can be resolved now.
        # The standard algorithm often relies on explicit END statements or flushing at the end.
        # In our case, since R doesn't have END IF;, we rely on the stack flush at the end or implicit end-of-block logic.
        # For now, we'll finalize markers only if the next token implies the end of their scope
        # or if we are at the end of input (handled in the beginning of the method).
        # Let's refine: finalize markers only if the next token is a statement separator (';') or end of input,
        # or if a new control flow statement starts that would interrupt the current one.
        # A safer bet is to finalize them during the final flush in the 'if self.current_index >= len...' block.
        # However, for IF without ELSE, we need to place the 'label_after_then:' when the IF block logically ends.
        # This happens implicitly when the next token is not part of the IF block's continuation.
        # We can simulate this by checking if the stack top is a THEN_END marker and the current token
        # is something that signals the end of the THEN part (e.g., another statement starter).
        # For simplicity in this step-wise version, we'll finalize THEN_END if it's on top and the next token
        # is not ELSE or another control flow continuation within the same block.
        # Let's implement this check carefully.
        # This is complex for a generic step. Finalizing in the flush is safer.
        # So, we will NOT finalize here, and rely on the final flush in the 'if self.current_index >= len...' block.

        # print(f"Stack: {self.stack}") # Debug
        # print(f"Output: {self.output}") # Debug

        # Continue if there are more input tokens OR the stack is not empty (needs flushing)
        return self.current_index < len(self.input_tokens) or bool(self.stack)


class RToOPZGUI:
    def __init__(self, parent_root, initial_code=""):
        self.opz_translator = OPZTranslator()

        self.window = tk.Toplevel(parent_root)
        self.window.title("Перевод в Обратную Польскую Запись (ОПЗ)")
        self.window.geometry("1200x800")
        self.window.configure(bg='#f0f0f0')

        # --- Main Frame ---
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1) # Code column
        main_frame.columnconfigure(3, weight=1) # OPZ column
        main_frame.rowconfigure(1, weight=1) # Text areas row
        main_frame.rowconfigure(3, weight=1) # History row

        # --- Input Code Section ---
        ttk.Label(main_frame, text="Входной код R:", font=("Consolas", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.code_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=40, height=15, bg='#ffffff', fg='#000000', font=("Consolas", 10))
        self.code_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # --- Controls ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=(5, 5), sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(button_frame, text="Запустить (всё)", command=self.run_all)
        self.run_button.grid(row=0, column=0, padx=(0, 5))
        self.step_button = ttk.Button(button_frame, text="Следующий шаг", command=self.step)
        self.step_button.grid(row=0, column=1, padx=(0, 5))
        self.reset_button = ttk.Button(button_frame, text="Сброс", command=self.reset)
        self.reset_button.grid(row=0, column=2, padx=(0, 5))
        self.load_button = ttk.Button(button_frame, text="Загрузить из файла", command=self.load_code_from_file)
        self.load_button.grid(row=0, column=3)

        # --- Stack Section ---
        ttk.Label(main_frame, text="Стек:", font=("Consolas", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=(5, 5))
        self.stack_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=20, height=15, bg='#e6f3ff', fg='#0000cc', font=("Consolas", 10))
        self.stack_text.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 5))

        # --- Output (OPZ) Section ---
        ttk.Label(main_frame, text="Выходная строка (ОПЗ):", font=("Consolas", 10, "bold")).grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        self.output_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=40, height=15, bg='#f0fff0', fg='#006600', font=("Consolas", 10))
        self.output_text.grid(row=1, column=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        # --- History Section ---
        ttk.Label(main_frame, text="История шагов:", font=("Consolas", 10, "bold")).grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))
        self.history_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=110, height=8, bg='#fafafa', fg='#333333', font=("Consolas", 9))
        self.history_text.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # --- Status Label ---
        self.status_label = ttk.Label(main_frame, text="Готов к переводу.", foreground="blue")
        self.status_label.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E))

        # Initialize with provided code
        self.code_text.insert(tk.END, initial_code)
        self.reset()

    def load_code_from_file(self):
        filename = filedialog.askopenfilename(
            title="Открыть R-скрипт",
            filetypes=[("R Script Files", "*.R *.r"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    content = file.read()
                self.code_text.delete(1.0, tk.END)
                self.code_text.insert(tk.END, content)
                self.reset()
                self.status_label.config(text=f"Загружен файл: {filename}", foreground="blue")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{str(e)}")

    def run_all(self):
        self.reset()
        code = self.code_text.get(1.0, tk.END).strip()
        if not code:
            self.status_label.config(text="Входной код пуст!", foreground="red")
            return

        self.opz_translator.tokenize_input(code)
        self.history_text.delete(1.0, tk.END)
        self.history_text.insert(tk.END, "=== Начало ===\n")
        self.history_text.insert(tk.END, f"Вход: {' '.join([t.value for t in self.opz_translator.input_tokens])}\n")
        self.history_text.insert(tk.END, f"Стек: {self.opz_translator.stack}\n")
        self.history_text.insert(tk.END, f"Выход: {' '.join(self.opz_translator.output)}\n---\n")

        while self.opz_translator.translate_step():
            if self.opz_translator.errors:
                break
            self.update_display()
            remaining_input = ' '.join([t.value for t in self.opz_translator.input_tokens[self.opz_translator.current_index:]])
            self.history_text.insert(tk.END, f"Вход: {remaining_input}\n")
            self.history_text.insert(tk.END, f"Стек: {self.opz_translator.stack}\n")
            self.history_text.insert(tk.END, f"Выход: {' '.join(self.opz_translator.output)}\n---\n")

        self.update_display()
        if self.opz_translator.errors:
            self.status_label.config(text=f"Ошибка: {self.opz_translator.errors[0]}", foreground="red")
            self.history_text.insert(tk.END, f"ОШИБКА: {self.opz_translator.errors[0]}\n")
        else:
            self.status_label.config(text="Перевод завершён успешно.", foreground="green")
            self.history_text.insert(tk.END, "=== Конец ===\n")


    def step(self):
        if not self.opz_translator.input_tokens and self.opz_translator.current_index == 0:
            # First step: tokenize input
            code = self.code_text.get(1.0, tk.END).strip()
            if not code:
                self.status_label.config(text="Входной код пуст!", foreground="red")
                return
            self.opz_translator.tokenize_input(code)
            self.history_text.insert(tk.END, "=== Начало пошагового режима ===\n")
            self.history_text.insert(tk.END, f"Вход: {' '.join([t.value for t in self.opz_translator.input_tokens])}\n")
            self.history_text.insert(tk.END, f"Стек: {self.opz_translator.stack}\n")
            self.history_text.insert(tk.END, f"Выход: {' '.join(self.opz_translator.output)}\n---\n")

        if self.opz_translator.errors:
             self.status_label.config(text=f"Ошибка: {self.opz_translator.errors[0]}", foreground="red")
             return

        has_more_steps = self.opz_translator.translate_step()

        self.update_display()
        if self.opz_translator.errors:
            self.status_label.config(text=f"Ошибка: {self.opz_translator.errors[0]}", foreground="red")
            self.history_text.insert(tk.END, f"ОШИБКА: {self.opz_translator.errors[0]}\n")
        else:
            remaining_input = ' '.join([t.value for t in self.opz_translator.input_tokens[self.opz_translator.current_index:]])
            self.history_text.insert(tk.END, f"Вход: {remaining_input}\n")
            self.history_text.insert(tk.END, f"Стек: {self.opz_translator.stack}\n")
            self.history_text.insert(tk.END, f"Выход: {' '.join(self.opz_translator.output)}\n---\n")
            if not has_more_steps:
                 self.status_label.config(text="Перевод завершён успешно.", foreground="green")
                 self.history_text.insert(tk.END, "=== Конец ===\n")


    def reset(self):
        self.opz_translator.reset()
        self.stack_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.history_text.delete(1.0, tk.END)
        self.status_label.config(text="Состояние сброшено.", foreground="blue")

    def update_display(self):
        self.stack_text.delete(1.0, tk.END)
        self.stack_text.insert(tk.END, str(self.opz_translator.stack))

        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, " ".join(map(str, self.opz_translator.output)))


# --- Help Window Class ---
class HelpWindow:
    def __init__(self, parent, title, text, width=800, height=600):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg='#f0f0f0')

        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        help_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            state=tk.NORMAL,
            font=('Consolas', 10)
        )
        scrollbar_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=help_text.yview)
        scrollbar_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=help_text.xview)
        help_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        help_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))

        help_text.insert(tk.END, text)
        help_text.config(state=tk.DISABLED)

        ttk.Button(main_frame, text="Закрыть", command=self.window.destroy, width=15).grid(row=1, column=0, pady=15)


# --- Main GUI class ---
class RLexerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Лексический анализатор языка R")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')

        # --- Font Setup ---
        self.setup_fonts()

        # --- Variables ---
        self.lexer = RLexer()
        self.current_file = None
        self.is_analyzed = False

        # --- Setup UI ---
        self.setup_ui()

    def setup_fonts(self):
        self.default_font = "Arial"
        self.font_size = 10
        self.small_font_size = 9
        self.large_font_size = 11

    def setup_ui(self):
        # --- Menu Bar ---
        MENU_FONT = (self.default_font, max(8, self.font_size - 2))

        menubar = tk.Menu(self.root, font=MENU_FONT)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, font=MENU_FONT)
        menubar.add_cascade(label="Файл", menu=file_menu, font=MENU_FONT)
        file_menu.add_command(label="Открыть файл", command=self.open_file, font=MENU_FONT)
        file_menu.add_command(label="Сохранить результат", command=self.save_results, font=MENU_FONT)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit, font=MENU_FONT)

        analyze_menu = tk.Menu(menubar, tearoff=0, font=MENU_FONT)
        menubar.add_cascade(label="Анализ", menu=analyze_menu, font=MENU_FONT)
        analyze_menu.add_command(label="Запустить анализ", command=self.analyze, font=MENU_FONT)
        analyze_menu.add_command(label="Очистить всё", command=self.clear_all, font=MENU_FONT)

        view_menu = tk.Menu(menubar, tearoff=0, font=MENU_FONT)
        menubar.add_cascade(label="Просмотр", menu=view_menu, font=MENU_FONT)
        view_menu.add_command(label="Полная последовательность лексем", command=self.show_full_sequence, font=MENU_FONT)
        view_menu.add_command(label="Программа с лексемами", command=self.show_lexeme_program, font=MENU_FONT)

        # --- НОВОЕ МЕНЮ ОПЗ ---
        opz_menu = tk.Menu(menubar, tearoff=0, font=MENU_FONT)
        menubar.add_cascade(label="ОПЗ", menu=opz_menu, font=MENU_FONT)
        opz_menu.add_command(label="Перевести в ОПЗ", command=self.open_opz_window, font=MENU_FONT)
        # ----------------------

        examples_menu = tk.Menu(menubar, tearoff=0, font=MENU_FONT)
        menubar.add_cascade(label="Примеры", menu=examples_menu, font=MENU_FONT)
        examples_menu.add_command(label="Корректный код R", command=lambda: self.load_example("correct"), font=MENU_FONT)
        examples_menu.add_command(label="Ошибки в числах", command=lambda: self.load_example("errors"), font=MENU_FONT)
        examples_menu.add_command(label="Множественные точки", command=lambda: self.load_example("dots"), font=MENU_FONT)
        examples_menu.add_command(label="Буквы в числах", command=lambda: self.load_example("letters"), font=MENU_FONT)
        examples_menu.add_command(label="Корректные числа", command=lambda: self.load_example("correct_numbers"), font=MENU_FONT)

        help_menu = tk.Menu(menubar, tearoff=0, font=MENU_FONT)
        menubar.add_cascade(label="Справка", menu=help_menu, font=MENU_FONT)
        help_menu.add_command(label="О программе", command=self.show_about, font=MENU_FONT)
        help_menu.add_command(label="Синтаксис R", command=self.show_r_syntax, font=MENU_FONT)
        help_menu.add_command(label="Типы ошибок", command=self.show_error_types, font=MENU_FONT)

        # --- Bindings ---
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_results())
        self.root.bind('<F5>', lambda e: self.analyze())

        # --- Main Layout ---
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        info_frame = ttk.LabelFrame(main_frame, text="Информация", padding="10")
        info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        info_frame.columnconfigure(1, weight=1)
        ttk.Label(info_frame, text="Файл: ", font=(self.default_font, self.font_size, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5)
        self.file_label = ttk.Label(info_frame, text="Не выбран", foreground="gray", font=(self.default_font, self.font_size))
        self.file_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        ttk.Label(info_frame, text="Статус: ", font=(self.default_font, self.font_size, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.status_label = ttk.Label(info_frame, text="Готов к работе", foreground="green", font=(self.default_font, self.font_size, 'bold'))
        self.status_label.grid(row=0, column=3, sticky=tk.W, padx=5)

        button_frame = ttk.Frame(info_frame)
        button_frame.grid(row=0, column=4, padx=(50, 0))
        ttk.Button(button_frame, text="Открыть файл", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Запустить анализ", command=self.analyze).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить", command=self.clear_code).pack(side=tk.LEFT, padx=5)

        left_frame = ttk.LabelFrame(main_frame, text="Исходный код на R", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        self.code_text = scrolledtext.ScrolledText(
            left_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.font_size),
            background='#ffffff',
            foreground='#000000',
            insertbackground='black'
        )
        self.code_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self._setup_code_tags()

        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=1, column=0, pady=15)
        ttk.Button(control_frame, text="Открыть файл", command=self.open_file, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Запустить анализ", command=self.analyze, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Очистить", command=self.clear_code, width=20).pack(side=tk.LEFT, padx=5)

        right_frame = ttk.LabelFrame(main_frame, text="Результаты анализа", padding="10")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self._setup_notebook_tabs()

        stats_frame = ttk.LabelFrame(main_frame, text="Статистика", padding="10")
        stats_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        stats_frame.columnconfigure(5, weight=1)
        stats_frame.columnconfigure(7, weight=1)
        self.stats_labels = {}

        stats_items = [
            ("Всего лексем: ", "0", 0),
            ("Идентификаторов: ", "0", 2),
            ("Чисел: ", "0", 4),
            ("Строк: ", "0", 6),
            ("Комментариев: ", "0", 8),
            ("Ключевых слов: ", "0", 10),
            ("Операций: ", "0", 12),
            ("Ошибок: ", "0", 14)
        ]
        for i, (label, value, col) in enumerate(stats_items):
            ttk.Label(stats_frame, text=label, font=(self.default_font, self.font_size, 'bold')).grid(row=0, column=col, sticky=tk.W, padx=(10, 5))
            lbl_var = tk.StringVar(value=value)
            self.stats_labels[label] = lbl_var
            ttk.Label(stats_frame, textvariable=lbl_var, font=(self.default_font, self.font_size, 'bold')).grid(row=0, column=col+1, sticky=tk.W, padx=(0, 20))

        # --- Progress Bar (initially hidden) ---
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.progress.grid_remove() # Hide initially

    def _setup_code_tags(self):
        self.code_text.tag_configure("keyword", foreground="blue", font=(self.default_font, self.font_size, 'bold'))
        self.code_text.tag_configure("identifier", foreground="black")
        self.code_text.tag_configure("number", foreground="red")
        self.code_text.tag_configure("string", foreground="green")
        self.code_text.tag_configure("comment", foreground="gray", font=(self.default_font, self.font_size, 'italic'))
        self.code_text.tag_configure("operation", foreground="purple")
        self.code_text.tag_configure("delimiter", foreground="orange")
        self.code_text.tag_configure("error", background="yellow", foreground="red")

    def _setup_notebook_tabs(self):
        # Tokens Tab
        self.tokens_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tokens_frame, text="Лексемы")
        self.tokens_frame.columnconfigure(0, weight=1)
        self.tokens_frame.rowconfigure(0, weight=1)
        self.tokens_text = scrolledtext.ScrolledText(
            self.tokens_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.small_font_size),
            background='#ffffff',
            foreground='#000000'
        )
        self.tokens_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Full Tables Tab
        self.tables_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tables_frame, text="Таблицы")
        self.tables_frame.columnconfigure(0, weight=1)
        self.tables_frame.rowconfigure(0, weight=1)
        self.tables_text = scrolledtext.ScrolledText(
            self.tables_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.small_font_size),
            background='#f9f9f9',
            foreground='#000000'
        )
        self.tables_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Errors Tab
        self.errors_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.errors_frame, text="Ошибки")
        self.errors_frame.columnconfigure(0, weight=1)
        self.errors_frame.rowconfigure(0, weight=1)
        self.errors_text = scrolledtext.ScrolledText(
            self.errors_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.small_font_size),
            background='#fff0f0',
            foreground='#ff0000'
        )
        self.errors_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Identifiers Tree Tab
        self.identifiers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.identifiers_frame, text="Идентификаторы")
        self.identifiers_frame.columnconfigure(0, weight=1)
        self.identifiers_frame.rowconfigure(0, weight=1)
        self.identifiers_tree = ttk.Treeview(
            self.identifiers_frame,
            columns=('ID', 'Имя'),
            show='headings',
            height=15
        )
        self.identifiers_tree.heading('ID', text='ID')
        self.identifiers_tree.heading('Имя', text='Имя')
        self.identifiers_tree.column('ID', width=120, minwidth=80)
        self.identifiers_tree.column('Имя', width=350, minwidth=200)
        scrollbar_id = ttk.Scrollbar(self.identifiers_frame, orient=tk.VERTICAL, command=self.identifiers_tree.yview)
        self.identifiers_tree.configure(yscrollcommand=scrollbar_id.set)
        self.identifiers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_id.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Numbers Tree Tab
        self.numbers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.numbers_frame, text="Числа")
        self.numbers_frame.columnconfigure(0, weight=1)
        self.numbers_frame.rowconfigure(0, weight=1)
        self.numbers_tree = ttk.Treeview(
            self.numbers_frame,
            columns=('ID', 'Значение'),
            show='headings',
            height=15
        )
        self.numbers_tree.heading('ID', text='ID')
        self.numbers_tree.heading('Значение', text='Значение')
        self.numbers_tree.column('ID', width=120, minwidth=80)
        self.numbers_tree.column('Значение', width=350, minwidth=200)
        scrollbar_num = ttk.Scrollbar(self.numbers_frame, orient=tk.VERTICAL, command=self.numbers_tree.yview)
        self.numbers_tree.configure(yscrollcommand=scrollbar_num.set)
        self.numbers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_num.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Comments Tree Tab
        self.comments_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.comments_frame, text="Комментарии")
        self.comments_frame.columnconfigure(0, weight=1)
        self.comments_frame.rowconfigure(0, weight=1)
        self.comments_tree = ttk.Treeview(
            self.comments_frame,
            columns=('ID', 'Текст'),
            show='headings',
            height=15
        )
        self.comments_tree.heading('ID', text='ID')
        self.comments_tree.heading('Текст', text='Текст')
        self.comments_tree.column('ID', width=120, minwidth=80)
        self.comments_tree.column('Текст', width=600, minwidth=400)
        scrollbar_com = ttk.Scrollbar(self.comments_frame, orient=tk.VERTICAL, command=self.comments_tree.yview)
        self.comments_tree.configure(yscrollcommand=scrollbar_com.set)
        self.comments_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_com.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def load_example(self, example_type):
        examples = {
            "correct": """# Пример корректного кода на R
calculate_stats <- function(data) {
  mean_val <- mean(data)
  sd_val <- sd(data)

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

x <- 123.45
y <- 2.5e-3
z <- 100
w <- 1.6E-19
""",
            "correct_numbers": """#ОРРЕКТНЫХ чисел в R
a <- 42
b <- 0
c <- 1000000
d <- -123
e <- 123.45
g <- 0.5
h <- -3.14
i <- 8.05
j <- 2.5e-3
k <- 1.6E-19
l <- 3e5
n <- 123.e-4

x <- c(1, 2, 3)
y <- list$element
z <- 1.2
""",
            "errors": """# Примеры НЕКОРРЕКТНЫХ чисел (ошибки)
a <- 123.45. # Ошибка: множественная точка
b <- 123abc   # Ошибка: буква в числе
c <- 1.2e3.4 # Ошибка: точка в экспоненте
""",
            "dots": """# Примеры с точками
a <- 123..45 # Ошибка: ..
b <- 123... # OK as operator, but might be handled as error depending on context
c <- .73 # OK: число, начинающееся с точки
d <- ... # Operator
""",
            "letters": """# Примеры букв в числах
a <- 123a
b <- 1.2e3x
c <- 4e5f
"""
        }
        if example_type in examples:
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, examples[example_type])
            self.current_file = None
            self._clear_code_tags()
            name_map = {
                "correct": "Пример: корректный код",
                "correct_numbers": "Пример: корректные числа",
                "errors": "Пример: ошибки в числах",
                "dots": "Пример: использование точки",
                "letters": "Пример: буквы в числах"
            }
            self.file_label.config(text=name_map.get(example_type, "Пример"), foreground="green")

    def _clear_code_tags(self):
        for tag in ["keyword", "string", "comment", "number", "operation", "delimiter", "error"]:
            self.code_text.tag_remove(tag, 1.0, tk.END)

    def open_file(self):
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
                self._clear_code_tags()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{str(e)}")

    def save_results(self):
        if not self.is_analyzed:
            messagebox.showwarning("Предупреждение", "Сначала анализ!")
            return

        filename = filedialog.asksaveasfilename(
            title="Сохранить результаты анализа",
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
                    f.write(f"{'№':<6} {'Код':<8} {'Значение':<25} {'Строка':<8} {'Колонка':<8} {'Статус':<15}\n")
                    f.write("-" * 90 + "\n")
                    for i, token in enumerate(self.lexer.token_sequence, 1):
                        status = "ОШИБКА" if token.lex_type == LexemType.ERROR else "OK"
                        f.write(f"{i:<6} {token.code:<8} {token.value:<25} {token.line:<8} {token.column:<8} {status:<15}\n")
                        if token.error_msg:
                            f.write(f"{'':<6} {'└─':<8} {token.error_msg}\n")
                    f.write("\n" + "=" * 80 + "\n")

                    f.write("ТАБЛИЦЫ ЛЕКСЕМ:\n")
                    f.write("=" * 80 + "\n")
                    f.write(self.lexer.generate_tables_report())
                    f.write("\n" + "=" * 80 + "\n")

                    f.write("ПРОГРАММА С ЗАМЕНОЙ НА ЛЕКСЕМЫ\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(self.lexer.generate_lexeme_program())

                messagebox.showinfo("Успех", f"Результаты сохранены в файл:\n{filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")

    def analyze(self):
        code = self.code_text.get(1.0, tk.END)
        if not code.strip():
            messagebox.showwarning("Предупреждение", "Нет кода для анализа!")
            return

        self.progress.grid()
        self.progress.start()
        self.status_label.config(text="Выполняется анализ...", foreground="orange")
        self.root.update()

        try:
            tokens = self.lexer.tokenize(code)
            self.update_results()
            self.update_statistics()
            self.highlight_errors()
            if self.lexer.errors:
                self.status_label.config(text=f"Анализ завершен. Найдено ошибок: {len(self.lexer.errors)}", foreground="red")
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
        if not self.lexer.token_sequence:
            messagebox.showwarning("Предупреждение", "Нет данных для отображения! Сначала выполните анализ.")
            return

        full_window = tk.Toplevel(self.root)
        full_window.title("Полная последовательность лексем")
        full_window.geometry("1200x700")
        full_window.configure(bg='#f0f0f0')
        full_window.option_add('*Font', (self.default_font, self.small_font_size))

        main_frame = ttk.Frame(full_window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        full_window.columnconfigure(0, weight=1)
        full_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        title_label = ttk.Label(main_frame, text="ПОЛНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ", font=(self.default_font, self.large_font_size, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        full_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=(self.default_font, self.small_font_size),
            background='#ffffff'
        )
        full_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self._insert_full_sequence_content(full_text)

        ttk.Button(main_frame, text="Закрыть", command=full_window.destroy, width=15).grid(row=2, column=0, pady=15)

    def _insert_full_sequence_content(self, text_widget):
        text_widget.insert(1.0, "=" * 100 + "\n")
        text_widget.insert(2.0, f"ПОЛНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ ({len(self.lexer.token_sequence)} шт.)\n")
        text_widget.insert(3.0, "=" * 100 + "\n")
        text_widget.insert(4.0, f"{'№':<6} {'Код':<10} {'Значение':<30} {'Позиция':<15} {'Статус':<10}\n")
        text_widget.insert(5.0, "-" * 100 + "\n")

        current_line = -1
        line_tokens = []
        for i, token in enumerate(self.lexer.token_sequence, 1):
            if token.line != current_line:
                if line_tokens:
                    text_widget.insert(tk.END, f"\n--- Строка {current_line} ---\n")
                    for j, t in enumerate(line_tokens, 1):
                        status = "ОШИБКА" if t.lex_type == LexemType.ERROR else "OK"
                        text_widget.insert(tk.END, f"{j:4d}. {t.code:8s}| {t.value:25s}| позиция {t.column:4d}| {status}\n")
                        if t.error_msg:
                            text_widget.insert(tk.END, f" └─ {t.error_msg}\n")
                line_tokens = []
                current_line = token.line
            line_tokens.append(token)

        # Insert the last batch of tokens
        if line_tokens:
            text_widget.insert(tk.END, f"\n--- Строка {current_line} ---\n")
            for j, t in enumerate(line_tokens, 1):
                status = "ОШИБКА" if t.lex_type == LexemType.ERROR else "OK"
                text_widget.insert(tk.END, f"{j:4d}. {t.code:8s}| {t.value:25s}| позиция {t.column:4d}| {status}\n")
                if t.error_msg:
                    text_widget.insert(tk.END, f" └─ {t.error_msg}\n")

    def show_lexeme_program(self):
        if not self.lexer.token_sequence:
            messagebox.showwarning("Предупреждение", "Нет данных для отображения! Сначала выполните анализ.")
            return

        lex_window = tk.Toplevel(self.root)
        lex_window.title("Программа с лексемами")
        lex_window.geometry("1200x800")
        lex_window.configure(bg='#f0f0f0')
        lex_window.option_add('*Font', (self.default_font, self.small_font_size))

        main_frame = ttk.Frame(lex_window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        lex_window.columnconfigure(0, weight=1)
        lex_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        title_label = ttk.Label(main_frame, text="ПРОГРАММА С ЗАМЕНОЙ НА ЛЕКСЕМЫ", font=(self.default_font, self.large_font_size, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        lex_program_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=(self.default_font, 12, "bold"),
            background='#ffffff'
        )
        scrollbar_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=lex_program_text.yview)
        lex_program_text.configure(yscrollcommand=scrollbar_y.set)

        lex_program_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))

        clean_lex_program = self.lexer.generate_clean_lexeme_program()
        lex_program_text.config(state=tk.NORMAL)  # Temporarily enable to insert
        lex_program_text.insert(tk.END, clean_lex_program)
        lex_program_text.config(state=tk.DISABLED)  # Disable again

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=15)
        ttk.Button(button_frame, text="Сохранить в файл", command=lambda: self.save_lexeme_program(clean_lex_program)).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Закрыть", command=lex_window.destroy).pack(side=tk.LEFT, padx=10)

    def save_lexeme_program(self, content):
        filename = filedialog.asksaveasfilename(
            title="Сохранить программу с лексемами",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Успех", f"Программа сохранена в файл:\n{filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")

    def update_results(self):
        self._update_tokens_text()
        self._update_tables_text()
        self._update_errors_text()
        self._update_trees()

    def _update_tokens_text(self):
        self.tokens_text.delete(1.0, tk.END)
        self.tokens_text.insert(1.0, "ПОСЛЕДОВАТЕЛЬНОСТЬ ЛЕКСЕМ (первые 100)\n")
        self.tokens_text.insert(2.0, "=" * 90 + "\n")
        self.tokens_text.insert(3.0, f"{'№':<6} {'Код':<8} {'Значение':<25} {'Строка':<8} {'Колонка':<8} {'Статус':<15}\n")
        self.tokens_text.insert(4.0, "-" * 90 + "\n")
        for i, token in enumerate(self.lexer.token_sequence[:100], 1):  # Show first 100
            status = "ОШИБКА" if token.lex_type == LexemType.ERROR else "OK"
            self.tokens_text.insert(tk.END, f"{i:<6} {token.code:<8} {token.value:<25} {token.line:<8} {token.column:<8} {status:<15}\n")
            if token.error_msg:
                self.tokens_text.insert(tk.END, f"{'':<6} {'└─':<8} {token.error_msg}\n")
        if len(self.lexer.token_sequence) > 100:
            self.tokens_text.insert(tk.END, f"\n... и ещё {len(self.lexer.token_sequence) - 100} лексем(ы)\n")

    def _update_tables_text(self):
        self.tables_text.delete(1.0, tk.END)
        report_content = self.lexer.generate_tables_report()
        self.tables_text.insert(tk.END, report_content)

    def _update_errors_text(self):
        self.errors_text.delete(1.0, tk.END)

        if not self.lexer.errors:
            self.errors_text.insert(tk.END, "Ошибок не найдено.\n")
            return

        # Group errors by type
        dot_errors = [e for e in self.lexer.errors if "Множественное использование точки" in e]
        letter_errors = [e for e in self.lexer.errors if "Буква в числе" in e or "некорректное построение числа" in e]
        other_errors = [e for e in self.lexer.errors if e not in dot_errors and e not in letter_errors]

        if dot_errors:
            self.errors_text.insert(tk.END, "📌 МНОЖЕСТВЕННОЕ ИСПОЛЬЗОВАНИЕ ТОЧКИ:\n")
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

    def _update_trees(self):
        # Clear all trees
        for tree in [self.identifiers_tree, self.numbers_tree, self.comments_tree]:
            for item in tree.get_children():
                tree.delete(item)

        # Populate Identifiers Tree
        for name, idx in sorted(self.lexer.identifiers.items(), key=lambda x: x[1]):
            self.identifiers_tree.insert('', tk.END, values=(f"I{idx:04d}", name))

        # Populate Numbers Tree
        for num, idx in sorted(self.lexer.numbers.items(), key=lambda x: x[1]):
            self.numbers_tree.insert('', tk.END, values=(f"N{idx:04d}", num))

        # Populate Comments Tree
        for comment, idx in sorted(self.lexer.comments.items(), key=lambda x: x[1]):
            self.comments_tree.insert('', tk.END, values=(f"C{idx:04d}", comment))

    def update_statistics(self):
        stats = self.lexer.get_summary()
        self.stats_labels["Всего лексем: "].set(str(stats["total_tokens"]))
        self.stats_labels["Идентификаторов: "].set(str(stats["identifiers"]))
        self.stats_labels["Чисел: "].set(str(stats["numbers"]))
        self.stats_labels["Строк: "].set(str(stats["strings"]))
        self.stats_labels["Комментариев: "].set(str(stats["comments"]))
        self.stats_labels["Ключевых слов: "].set(str(stats["keywords"]))
        self.stats_labels["Операций: "].set(str(stats["operations"]))
        self.stats_labels["Ошибок: "].set(str(stats["errors"]))

        # Color the error count
        if stats["errors"] > 0:
            self.stats_labels["Ошибок: "].set(str(stats["errors"]))
        else:
            self.stats_labels["Ошибок: "].set(str(stats["errors"]))

    def highlight_errors(self):
        for token in self.lexer.token_sequence:
            if token.lex_type == LexemType.ERROR:
                start = f"{token.line}.{token.column - 1}"
                end = f"{start} + {len(token.value)} chars"
                self.code_text.tag_add("error", start, end)

    def clear_code(self):
        self.code_text.delete(1.0, tk.END)
        self.current_file = None
        self.file_label.config(text="Не выбран", foreground="gray")
        self._clear_code_tags()

    def clear_all(self):
        self.clear_code()
        for frame in [self.tokens_frame, self.tables_frame, self.errors_frame, self.identifiers_frame, self.numbers_frame, self.comments_frame]:
            for child in frame.winfo_children():
                if isinstance(child, tk.Text) or isinstance(child, ttk.Treeview):
                    child.delete(1.0, tk.END)
        for item in self.identifiers_tree.get_children():
            self.identifiers_tree.delete(item)
        for item in self.numbers_tree.get_children():
            self.numbers_tree.delete(item)
        for item in self.comments_tree.get_children():
            self.comments_tree.delete(item)
        for label in self.stats_labels:
            self.stats_labels[label].config(text="0", foreground="blue")
        self.lexer.reset()
        self.status_label.config(text="Готов к работе", foreground="green")

    def show_about(self):
        about_text = f"""
Краснодар 2026

        """
        HelpWindow(self.root, "О программе", about_text, width=600, height=400)

    def show_r_syntax(self):
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
%in%, %*%, %>%

Комментарии:
# Однострочный комментарий

Строки:
'в одинарных кавычках' или "в двойных кавычках"

Разделители:
, ; : :: ::: ( ) [ ] [[ ]] { } ` $ @
        """
        HelpWindow(self.root, "Синтаксис R", syntax_text, width=700, height=500)

    def show_error_types(self):
        error_text = f"""ТИПЫ ОШИБОК, ОТЛАВЛИВАЕМЫХ АНАЛИЗАТОРОМ:

НЕКОРРЕКТНОЕ ИСПОЛЬЗОВАНИЕ ТОЧКИ:
• Множественные точки: 123.23.3, 1.2.3.4, 12.34.56.78
• Несколько точек подряд: 123..45, 1.2..3, 5..2, 1...7
• Точка в экспоненте: 1.5e2.3, 2.5e-3.4

БУКВЫ В ЧИСЛАХ:
• Буквы после цифр: 123a, 45x, 67y
• Буквы внутри числа: 1a2a3, 123b213a, 45x67y89
• Буквы в экспоненте: 2.5ea, 1.3e2b

НЕКОРРЕКТНОЕ ПОСТРОЕНИЕ ЧИСЛА:
• Начинается с цифры, содержит буквы: 123abc
• Смешанный формат: 123a456

НЕЗАКРЫТЫЕ СТРОКИ:
• Отсутствует закрывающая кавычка

НЕИЗВЕСТНЫЕ СИМВОЛЫ:
• Символы, не принадлежащие алфавиту языка
        """
        HelpWindow(self.root, "Типы ошибок", error_text, width=700, height=600)

    # --- Новый метод для открытия окна ОПЗ ---
    def open_opz_window(self):
        code = self.code_text.get(1.0, tk.END).strip()
        RToOPZGUI(self.root, initial_code=code)


def main():
    root = tk.Tk()
    app = RLexerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
