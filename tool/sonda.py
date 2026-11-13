#!/usr/bin/env python3
"""Sonda de leitura: imprime janelas de contexto em torno de agulhas num
arquivo minificado. Somente leitura, nao modifica nada.

Uso: python sonda.py <arquivo> <agulha1> <agulha2> ...
"""
import io
import sys


def main():
    path = sys.argv[1]
    with io.open(path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    for needle in sys.argv[2:]:
        occurrences = 0
        i = 0
        windows = []
        while True:
            j = text.find(needle, i)
            if j < 0:
                break
            occurrences += 1
            if len(windows) < 10:
                a = max(0, j - 110)
                b = min(len(text), j + len(needle) + 110)
                windows.append(text[a:b])
            i = j + len(needle)
        print(f'=== {needle!r}: {occurrences} ocorrencia(s)')
        for w in windows:
            print('    ' + w.replace('\n', '\\n'))
        print()


if __name__ == '__main__':
    main()
