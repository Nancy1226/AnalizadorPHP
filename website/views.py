import re
from flask import Blueprint, render_template, request

views = Blueprint('views', __name__)

php_keywords = ["echo"]
php_symbols = ["<?php", "?>", ";", "{", "}", "(", ")"]
identifier_pattern = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
string_pattern = re.compile(r'"[^"]*"|\'[^\']*\'')

def tokenize_php_code(code):
    tokens = []
    current_token = ""
    line_number = 1
    i = 0
    in_php_block = False

    while i < len(code):
        if code[i] == "\n":
            line_number += 1

        if not in_php_block and code[i].isspace():
            i += 1
            continue

        if code[i:i+5] == "<?php":
            in_php_block = True
            tokens.append({'value': "<?php", 'line': line_number, 'type': 'symbol'})
            i += 5
            continue

        if code[i:i+2] == "?>" and in_php_block:
            in_php_block = False
            tokens.append({'value': "?>", 'line': line_number, 'type': 'symbol'})
            i += 2
            continue

        if in_php_block:
            if code[i].isspace():
                if current_token:
                    tokens.append({'value': current_token, 'line': line_number, 'type': get_token_type(current_token)})
                    current_token = ""
                i += 1
                continue

            if code[i] in php_symbols:
                if current_token:
                    tokens.append({'value': current_token, 'line': line_number, 'type': get_token_type(current_token)})
                    current_token = ""
                tokens.append({'value': code[i], 'line': line_number, 'type': 'symbol'})
                i += 1
                continue

            # Handling string literals
            if code[i] in ['"', "'"]:
                quote_type = code[i]
                start_index = i
                i += 1
                while i < len(code) and code[i] != quote_type:
                    if code[i] == "\n":
                        line_number += 1
                    i += 1
                if i < len(code) and code[i] == quote_type:
                    i += 1
                tokens.append({'value': code[start_index:i], 'line': line_number, 'type': 'string'})
                continue

            current_token += code[i]
            i += 1

        else:
            i += 1

    if current_token:
        tokens.append({'value': current_token, 'line': line_number, 'type': get_token_type(current_token)})

    return tokens

def get_token_type(token):
    if token == "echo":
        return 'keyword'
    elif identifier_pattern.fullmatch(token):
        return 'identifier'
    elif token in php_symbols:
        return 'symbol'
    elif string_pattern.fullmatch(token):
        return 'string'
    return 'unknown'

def count_tokens(tokens):
    keywords = 0
    identifiers = 0
    symbols = 0
    strings = 0

    for token in tokens:
        if token['type'] == 'keyword':
            keywords += 1
        elif token['type'] == 'identifier':
            identifiers += 1
        elif token['type'] == 'symbol':
            symbols += 1
        elif token['type'] == 'string':
            strings += 1

    return {"keywords": keywords, "identifiers": identifiers, "symbols": symbols, "strings": strings}

def sintactic_analysis(tokens):
    errors = []
    stack = []
    php_opening_tag_found = False
    php_closing_tag_found = False
    last_token = None

    for token in tokens:
        if token['type'] == 'unknown':
            errors.append(f"Error en línea {token['line']}: Token desconocido '{token['value']}'")

        if token['value'] == '<?php':
            php_opening_tag_found = True
        elif token['value'] == '?>':
            php_closing_tag_found = True

        if token['value'] in ['(', '{']:
            stack.append(token)
        elif token['value'] in [')', '}']:
            if not stack:
                errors.append(f"Error en línea {token['line']}: '{token['value']}' no tiene pareja de apertura")
            else:
                top = stack.pop()
                if (top['value'] == '(' and token['value'] != ')') or (top['value'] == '{' and token['value'] != '}'):
                    errors.append(f"Error en línea {token['line']}: '{top['value']}' no coincide con '{token['value']}'")

        # Verificar terminación de declaraciones solo para ciertas palabras clave como "echo"
        if last_token and last_token['type'] == 'keyword' and last_token['value'] == 'echo':
            if token['type'] != 'symbol' or token['value'] != ';':
                errors.append(f"Error en línea {last_token['line']}: Falta ';' después de '{last_token['value']}'")

        last_token = token

    if php_opening_tag_found and not php_closing_tag_found:
        errors.append("Error: Falta el tag de cierre '?>' para el bloque PHP")
    
    if not php_opening_tag_found:
        errors.append("Error: Falta el tag de apertura '<?php' para el bloque PHP")
    
    if stack:
        for unclosed in stack:
            errors.append(f"Error en línea {unclosed['line']}: '{unclosed['value']}' no tiene pareja de cierre")

    if not errors:
        return "Estructura de código correcta."

    return "Errores sintácticos encontrados:\n" + "\n".join(errors)

@views.route('/', methods=['GET', 'POST'])
def index():
    codigo = ""
    if request.method == 'POST':
        codigo = request.form['codigo']
        tokens = tokenize_php_code(codigo)

        if not tokens:
            return render_template('home.html', error="No se ingresó código PHP", codigo=codigo)

        token_count = count_tokens(tokens)
        sintactico_result = sintactic_analysis(tokens)

        total_tokens = len(tokens)
        total_keywords = token_count["keywords"]
        total_identifiers = token_count["identifiers"]
        total_symbols = token_count["symbols"]
        total_strings = token_count["strings"]

        return render_template('home.html', tokens=tokens, total_tokens=total_tokens, total_keywords=total_keywords, total_identifiers=total_identifiers, total_symbols=total_symbols, total_strings=total_strings, codigo=codigo, sintactico_result=sintactico_result)
    
    return render_template('home.html', codigo=codigo)