#!/usr/bin/env python3
"""Varredura de leitura: procura agulhas em todos os arquivos .js de uma
arvore e reporta arquivo + contagem. Somente leitura.

Uso: python varredura.py <raiz> <agulha1> <agulha2> ...
"""
import io
import os
import sys


def main():
    root = sys.argv[1]
    needles = sys.argv[2:]
    counts = {n: {} for n in needles}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith('.js'):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with io.open(path, encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except OSError:
                continue
            for n in needles:
                c = text.count(n)
                if c:
                    counts[n][path] = c
    for n in needles:
        print(f'=== {n!r}')
        for path, c in sorted(counts[n].items()):
            print(f'    {c:5d}  {path}')
        if not counts[n]:
            print('    (nada)')
        print()


if __name__ == '__main__':
    main()
