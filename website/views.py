import re
from flask import Blueprint, render_template, request
import ply.yacc as yacc
from ply.lex import TOKEN

views = Blueprint('views', __name__)

custom_keywords = ["echo", "Inicio", "var1", "var2", "si", "ver", "fin", "proceso", "cadena"]
custom_symbols = [";", "{", "}", "(", ")", "=", "=="]
identifier_pattern = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
string_pattern = re.compile(r'"[^"]*"')
integer_pattern = re.compile(r'\d+')

# Tokenizer function
def tokenize_code(code):
    tokens = []
    current_token = ""
    line_number = 1
    i = 0

    while i < len(code):
        if code[i] == "\n":
            line_number += 1

        if code[i].isspace():
            if current_token:
                tokens.append({'value': current_token, 'line': line_number, 'type': get_token_type(current_token)})
                current_token = ""
            i += 1
            continue

        if code[i:i+2] == "==":
            if current_token:
                tokens.append({'value': current_token, 'line': line_number, 'type': get_token_type(current_token)})
                current_token = ""
            tokens.append({'value': "==", 'line': line_number, 'type': 'symbol'})
            i += 2
            continue

        if code[i] in custom_symbols:
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

    if current_token:
        tokens.append({'value': current_token, 'line': line_number, 'type': get_token_type(current_token)})

    return tokens

def get_token_type(token):
    if token in custom_keywords:
        return 'keyword'
    elif identifier_pattern.fullmatch(token):
        return 'identifier'
    elif token in custom_symbols:
        return 'symbol'
    elif string_pattern.fullmatch(token):
        return 'string'
    elif integer_pattern.fullmatch(token):
        return 'integer'
    return 'unknown'

def count_tokens(tokens):
    keywords = 0
    identifiers = 0
    symbols = 0
    strings = 0
    integers = 0

    for token in tokens:
        if token['type'] == 'keyword':
            keywords += 1
        elif token['type'] == 'identifier':
            identifiers += 1
        elif token['type'] == 'symbol':
            symbols += 1
        elif token['type'] == 'string':
            strings += 1
        elif token['type'] == 'integer':
            integers += 1

    return {"keywords": keywords, "identifiers": identifiers, "symbols": symbols, "strings": strings, "integers": integers}

def sintactic_analysis(tokens):
    errors = []
    stack = []
    opening_keyword_found = False
    closing_keyword_found = False
    last_token = None

    for i, token in enumerate(tokens):
        if token['type'] == 'unknown':
            errors.append(f"Error en línea {token['line']}: Token desconocido '{token['value']}'")

        if token['value'] == 'Inicio' or token['value'] == 'inicio':
            opening_keyword_found = True
        elif token['value'] == 'fin' or token['value'] == 'Fin':
            closing_keyword_found = True

        if token['value'] in ['(', '{']:
            stack.append(token)
        elif token['value'] in [')', '}']:
            if not stack:
                errors.append(f"Error en línea {token['line']}: '{token['value']}' no tiene pareja de apertura")
            else:
                top = stack.pop()
                if (top['value'] == '(' and token['value'] != ')') or (top['value'] == '{' and token['value'] != '}'):
                    errors.append(f"Error en línea {token['line']}: '{top['value']}' no coincide con '{token['value']}'")

        # Verificar terminación de declaraciones para var1 y var2 fuera del bloque si
        if token['value'] in ['var1', 'var2']:
            if i+1 >= len(tokens) or tokens[i+1]['value'] != '=':
                errors.append(f"Error en línea {token['line']}: Falta '=' después de '{token['value']}'")
            elif token['value'] == 'var1':
                if i+3 >= len(tokens) or tokens[i+2]['type'] != 'string' or (tokens[i+3]['value'] != ';' and not (tokens[i+3]['value'] == ')' and tokens[i+4]['value'] == '{')):
                    errors.append(f"Error en línea {token['line']}: Declaración de cadena 'var1' inválida. Debe ser 'var1=\"cadena\";' o estar en una condición 'si'.")
            elif token['value'] == 'var2':
                if i+3 >= len(tokens) or tokens[i+2]['type'] != 'integer' or (tokens[i+3]['value'] != ';' and not (tokens[i+3]['value'] == ')' and tokens[i+4]['value'] == '{')):
                    errors.append(f"Error en línea {token['line']}: Declaración de entero 'var2' inválida. Debe ser 'var2=5;' o estar en una condición 'si'.")

        # Verificar estructura de "si"
        if token['value'] == 'si':
            if i+7 >= len(tokens) or tokens[i+1]['value'] != '(' or tokens[i+5]['value'] != ')' or tokens[i+6]['value'] != '{' or tokens[i+7]['value'] != '}':
                errors.append(f"Error en línea {token['line']}: Estructura de 'si' inválida. Debe ser 'si (condición) {{ }}'")
            else:
                if tokens[i+3]['value'] not in ['=', '==']:
                    errors.append(f"Error en línea {token['line']}: Operador inválido en 'si'. Use '=' o '=='.")
                # elif tokens[i+2]['type'] not in ['identifier', 'integer', 'string'] or tokens[i+4]['type'] not in ['identifier', 'integer', 'string']:
                #     errors.append(f"Error en línea {token['line']}: Condición inválida en 'si'. Use identificadores, enteros o cadenas.")
                elif tokens[i+2]['type'] == 'identifier' and tokens[i+4]['type'] not in ['integer', 'string']:
                    errors.append(f"Error en línea {token['line']}: Condición inválida en 'si'. El identificador debe ser comparado con un entero o cadena.")
                elif tokens[i+2]['type'] == 'integer' and tokens[i+4]['type'] != 'integer':
                    errors.append(f"Error en línea {token['line']}: Condición inválida en 'si'. El entero debe ser comparado con otro entero.")
                elif tokens[i+2]['type'] == 'string' and tokens[i+4]['type'] != 'string':
                    errors.append(f"Error en línea {token['line']}: Condición inválida en 'si'. La cadena debe ser comparada con otra cadena.")

        # Verificar terminación de declaraciones solo para ciertas palabras clave como "echo"
        if last_token and last_token['type'] == 'keyword' and last_token['value'] == 'echo':
            if token['type'] != 'symbol' or token['value'] != ';':
                errors.append(f"Error en línea {last_token['line']}: Falta ';' después de '{last_token['value']}'")

        last_token = token

    if opening_keyword_found and not closing_keyword_found:
        errors.append("Error: Falta el keyword de cierre 'fin'")

    if not opening_keyword_found:
        errors.append("Error: Falta el keyword de apertura 'Inicio'")
    
    if stack:
        for unclosed in stack:
            errors.append(f"Error en línea {unclosed['line']}: '{unclosed['value']}' no tiene pareja de cierre")

    if not errors:
        return "Estructura de código correcta."

    return "Errores sintácticos encontrados:\n" + "\n".join(errors)

tokens = ('KEYWORD', 'IDENTIFIER', 'SYMBOL', 'STRING', 'INTEGER')

def p_statement_expr(p):
    '''statement : expression'''
    p[0] = p[1]

def p_expression_binop(p):
    '''expression : expression SYMBOL expression'''
    p[0] = ('binop', p[2], p[1], p[3])

def p_expression_group(p):
    '''expression : '(' expression ')' '''
    p[0] = p[2]

def p_expression_number(p):
    '''expression : INTEGER'''
    p[0] = ('number', p[1])

def p_expression_string(p):
    '''expression : STRING'''
    p[0] = ('string', p[1])

def p_expression_identifier(p):
    '''expression : IDENTIFIER'''
    p[0] = ('identifier', p[1])

def p_error(p):
    print(f"Syntax error at {p.value!r}")

parser = yacc.yacc()

@views.route('/', methods=['GET', 'POST'])
def index():
    codigo = ""
    if request.method == 'POST':
        codigo = request.form['codigo']
        tokens = tokenize_code(codigo)

        token_count = count_tokens(tokens)
        sintactico_result = sintactic_analysis(tokens)

        total_tokens = len(tokens)
        total_keywords = token_count["keywords"]
        total_identifiers = token_count["identifiers"]
        total_symbols = token_count["symbols"]
        total_strings = token_count["strings"]
        total_integers = token_count["integers"]

        return render_template('home.html', tokens=tokens, total_tokens=total_tokens, total_keywords=total_keywords, total_identifiers=total_identifiers, total_symbols=total_symbols, total_strings=total_strings, total_integers=total_integers, codigo=codigo, sintactico_result=sintactico_result)
    
    return render_template('home.html', codigo=codigo)