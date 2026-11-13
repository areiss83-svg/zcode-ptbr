#!/usr/bin/env python3
"""Divide o catalogo en em lotes para traducao e mostra o histograma de
prefixos de namespace.

Uso: python divide_lotes.py <en-catalog.json> <dir_saida> [tamanho_lote]
"""
import collections
import io
import json
import os
import re
import sys


def main():
    catalogo_path = sys.argv[1]
    saida_dir = sys.argv[2]
    tamanho = int(sys.argv[3]) if len(sys.argv) > 3 else 500

    with io.open(catalogo_path, encoding='utf-8') as f:
        catalogo = json.load(f)

    histograma = collections.Counter()
    for chave in catalogo:
        partes = chave.split('.')
        histograma[partes[0] if len(partes) > 1 else '(raiz)'] += 1

    print('=== namespaces (primeiro nivel) ===')
    for ns, c in histograma.most_common():
        print(f'{c:6d}  {ns}')

    chaves = sorted(catalogo)
    lotes = [chaves[i:i + tamanho] for i in range(0, len(chaves), tamanho)]
    os.makedirs(saida_dir, exist_ok=True)
    manifest = []
    for idx, lote in enumerate(lotes):
        nome = f'lote-{idx:02d}.json'
        caminho = os.path.join(saida_dir, nome)
        with io.open(caminho, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({k: catalogo[k] for k in lote}, f,
                      ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        manifest.append({'arquivo': nome, 'chaves': len(lote)})
    with io.open(os.path.join(saida_dir, 'lotes.json'), 'w',
                 encoding='utf-8', newline='\n') as f:
        json.dump({'total_chaves': len(chaves), 'tamanho_lote': tamanho,
                   'lotes': manifest}, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(f'=== {len(lotes)} lotes de {tamanho} em {saida_dir} ===')

    ph = re.compile(r'\{[^{}]+\}')
    com_ph = sum(1 for v in catalogo.values() if ph.search(v))
    print(f'chaves com placeholder: {com_ph}')


if __name__ == '__main__':
    main()
