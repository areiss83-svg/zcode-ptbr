#!/usr/bin/env python3
"""Valida e funde os lotes pt-BR contra o catalogo en.

Checagens:
  1. Conjunto de chaves: pt deve ser IGUAL ao en (nenhuma a mais, nenhuma a menos).
  2. Placeholders nomeados simples {name}: mesmo conjunto por chave.
  3. Balanceamento de chaves {} por valor (cobre plurais ICU {count, plural, ...}).
  4. Valor vazio em pt so quando vazio em en.
  5. Reporta quantos valores pt == en (nomes nativos/marca, esperado pequeno).

Uso: python valida_pt.py <en-catalog.json> <dir_lotes_pt> <saida.json>
"""
import glob
import io
import json
import re
import sys

PH_SIMPLES = re.compile(r'\{[A-Za-z0-9_]+\}')


def chaves_balanceadas(texto):
    prof = 0
    for ch in texto:
        if ch == '{':
            prof += 1
        elif ch == '}':
            prof -= 1
            if prof < 0:
                return False
    return prof == 0


def main():
    en_path, lotes_dir, saida = sys.argv[1:4]
    with io.open(en_path, encoding='utf-8') as f:
        en = json.load(f)

    pt = {}
    arquivos = sorted(glob.glob(lotes_dir.replace('\\', '/') + '/lote-*.json'))
    if not arquivos:
        raise SystemExit('nenhum lote pt encontrado em ' + lotes_dir)
    for caminho in arquivos:
        with io.open(caminho, encoding='utf-8') as f:
            lote = json.load(f)
        for k, v in lote.items():
            if k in pt:
                raise SystemExit(f'chave duplicada entre lotes: {k}')
            pt[k] = v

    erros = []
    faltando = [k for k in en if k not in pt]
    extras = [k for k in pt if k not in en]
    if faltando:
        erros.append(f'chaves ausentes no pt: {len(faltando)} (ex.: {faltando[:5]})')
    if extras:
        erros.append(f'chaves a mais no pt: {len(extras)} (ex.: {extras[:5]})')

    vazias = []
    desbal = []
    ph_div = []
    identicas = []
    for k in en:
        if k not in pt:
            continue
        ev, pv = en[k], pt[k]
        if pv == '' and ev != '':
            vazias.append(k)
        if not chaves_balanceadas(pv):
            desbal.append(k)
        if sorted(PH_SIMPLES.findall(ev)) != sorted(PH_SIMPLES.findall(pv)):
            ph_div.append(k)
        if pv == ev:
            identicas.append(k)

    if vazias:
        erros.append(f'valores pt vazios com en nao vazio: {vazias[:10]}')
    if desbal:
        erros.append(f'chaves {{}} desbalanceadas: {desbal[:10]}')
    if ph_div:
        erros.append(f'placeholders divergentes: {len(ph_div)} (ex.: {ph_div[:10]})')

    with io.open(saida, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(pt, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')

    print(f'en chaves   : {len(en)}')
    print(f'pt chaves   : {len(pt)}')
    print(f'pt == en    : {len(identicas)} (nomes nativos/marca esperados)')
    print(f'fuso pt     : {saida} ({len(pt)} chaves gravadas)')
    if erros:
        print('FALHAS:')
        for e in erros:
            print('  - ' + e)
        sys.exit(1)
    print('VALIDACAO OK')


if __name__ == '__main__':
    main()
