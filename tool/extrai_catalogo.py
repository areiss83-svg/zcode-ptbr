#!/usr/bin/env python3
"""Extrai o catalogo en-US dos fontes TS do repo para JSON plano e confere
as chaves contra o chunk IntlProvider do bundle instalado.

Uso: python extrai_catalogo.py <en-US.ts> <messages.ts> <IntlProvider.js> <saida.json>
"""
import io
import json
import sys


def _skip_ws(text, i, n):
    while i < n:
        ch = text[i]
        if ch in ' \t\r\n':
            i += 1
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j + 1
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
        else:
            break
    return i


def _read_string(text, i, n):
    q = text[i]
    if q not in '"\'':
        raise ValueError(f'esperava aspas em {i}: {text[i:i+40]!r}')
    i += 1
    out = []
    simples = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f',
               'v': '\v', '0': '\0'}
    while True:
        ch = text[i]
        if ch == '\\':
            nxt = text[i + 1]
            if nxt in simples:
                out.append(simples[nxt])
                i += 2
            elif nxt == 'x':
                out.append(chr(int(text[i + 2:i + 4], 16)))
                i += 4
            elif nxt == 'u':
                if text[i + 2] == '{':
                    j = text.index('}', i)
                    out.append(chr(int(text[i + 3:j], 16)))
                    i = j + 1
                else:
                    out.append(chr(int(text[i + 2:i + 6], 16)))
                    i += 6
            else:
                out.append(nxt)
                i += 2
        elif ch == q:
            return ''.join(out), i + 1
        else:
            out.append(ch)
            i += 1


def parse_object(text, start):
    """Percorre literal TS { "k": "v", ... } a partir da posicao do '{'.

    Devolve (dict, posicao apos o '}'). Rejeita espalhamentos (...)
    propositalmente: quem chama removeu-os antes.
    """
    result = {}
    i = start + 1
    n = len(text)
    while True:
        i = _skip_ws(text, i, n)
        if text[i] == '}':
            return result, i + 1
        if text[i] == ',':
            i += 1
            continue
        key, i = _read_string(text, i, n)
        i = _skip_ws(text, i, n)
        if text[i] != ':':
            raise ValueError(f'esperava ":" apos {key!r}: {text[i:i+40]!r}')
        i += 1
        i = _skip_ws(text, i, n)
        val, i = _read_string(text, i, n)
        result[key] = val
        i = _skip_ws(text, i, n)
        if text[i] == ',':
            i += 1


def main():
    en_path, msg_path, chunk_path, out_path = sys.argv[1:5]
    with io.open(en_path, encoding='utf-8') as f:
        en_src = f.read()
    with io.open(msg_path, encoding='utf-8') as f:
        msg_src = f.read()
    with io.open(chunk_path, encoding='utf-8', errors='replace') as f:
        chunk = f.read()

    en_src = en_src.replace('...requestSecurityMessagesEnUS,', '  ,')

    marcador = 'Record<string, string> = {'
    pos = en_src.index(marcador) + len(marcador) - 1
    catalogo, fim = parse_object(en_src, pos)
    resto = en_src[fim:fim + 60].strip()
    if not resto.startswith('export'):
        print(f'AVISO: sobra apos objeto: {resto[:60]!r}')

    marcador_msg = 'requestSecurityMessagesEnUS = {'
    pos_msg = msg_src.index(marcador_msg) + len(marcador_msg) - 1
    seguranca, _ = parse_object(msg_src, pos_msg)

    mesclado = dict(catalogo)
    for k, v in seguranca.items():
        mesclado.setdefault(k, v)

    ausentes = [k for k in mesclado if f'"{k}":' not in chunk]
    presentes = len(mesclado) - len(ausentes)

    with io.open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(mesclado, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')

    print(f'en-US puro     : {len(catalogo)} chaves')
    print(f'request-secur. : {len(seguranca)} chaves')
    print(f'mesclado       : {len(mesclado)} chaves')
    print(f'presentes no bundle 3.18.2 : {presentes}')
    print(f'ausentes no bundle        : {len(ausentes)}')
    for k in ausentes[:20]:
        print(f'    AUSENTE {k}')


if __name__ == '__main__':
    main()
