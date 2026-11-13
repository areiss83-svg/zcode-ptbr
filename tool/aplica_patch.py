#!/usr/bin/env python3
"""Aplica localizacao pt-BR ao app desktop ZCode (3.18.x).

Estrutura adaptada de tool/apply_ru_patch.py de mdn77/zcode-translation-ru
(MIT), reescrita para o mecanismo oficial multi-idioma introduzido na 3.18.0:
  1. Localiza resources/app.asar do ZCode instalado.
  2. Extrai o arquivo com o CLI oficial @electron/asar (via npx).
  3. Encontra os arquivos por CONTEUDO (sobrevive a mudanca de nome/hash):
     - modulo compartilhado de locale (renderer + copias em main/host/
       scheduler/extension-host): array SUPPORTED_LOCALES, mapa de nomes
       nativos e resolutor de tag de idioma;
     - chunk IntlProvider: mapa de catalogos S={"zh-CN":..,"en-US":..,...}.
  4. Injeta "pt-BR" no array, no mapa de nomes e no resolutor; insere o
     catalogo pt-BR inline no mapa de catalogos com fallback {...en,...pt}
     (o mesmo padrao oficial usado por ja/ru/ko).
  5. node --check em cada arquivo patcheado (como ESM), empacota de volta
     com @electron/asar (binarios nativos permanecem unpacked), verifica o
     resultado e faz backup timestamped antes do swap.

Uso:
  python aplica_patch.py                 # auto-detecta ZCode, patcheia
  python aplica_patch.py --asar CAMINHO  # caminho explicito do app.asar
  python aplica_patch.py --dry-run       # patcheia em memoria, nao grava

Requer Python 3.8+ e Node.js (npx) no PATH. Sem dependencias pip.
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

BT = '`'
Q = '"'  # variantes de aspas entre chunks do bundler
PT_LABEL = 'Português (Brasil)'
VAR_PT = '__zcodePtBr'

# ---------------------------------------------------------------------------
# helpers de literal JS (base russa, MIT)
# ---------------------------------------------------------------------------


def qx(s):
    return f'{BT}{s}{BT}'


def js_template_escape(value):
    """Escapa string simples para literal de template JS."""
    out = value.replace(chr(92), chr(92) * 2)
    out = out.replace(BT, chr(92) + BT)
    out = out.replace('${', chr(92) + '${')
    out = out.replace(chr(13), chr(92) + 'r')
    out = out.replace(chr(10), chr(92) + 'n')
    return out


def build_pt_literal(catalog):
    """Serializa o catalogo pt como literal JS: "key":`value`,..."""
    parts = []
    for k, v in catalog.items():
        parts.append(f'{Q}{k}{Q}:{qx(js_template_escape(v))}')
    return '{' + ','.join(parts) + '}'


# ---------------------------------------------------------------------------
# padroes de injecao (3.18.x)
# ---------------------------------------------------------------------------


def padrao_array(q):
    return re.compile(
        r'\[' + q + r'zh\-CN' + q + r',' + q + r'en\-US' + q + r',' + q +
        r'ja\-JP' + q + r',' + q + r'ru\-RU' + q + r',' + q + r'ko\-KR' + q +
        r'\]')


def substitui_array(texto, q, report):
    """Adiciona pt-BR ao array de locales suportadas."""
    novo = '[' + ','.join([q + 'zh-CN' + q, q + 'en-US' + q, q + 'ja-JP' + q,
                           q + 'ru-RU' + q, q + 'ko-KR' + q, q + 'pt-BR' + q]) + ']'
    texto, n = padrao_array(q).subn(novo.replace('\\', '\\\\'), texto)
    report['array locales (' + q + ')'] = n
    return texto, n


def corpo_nomes(q):
    """Mapa de nomes nativos: chaves sempre "..." e valores com aspas q."""
    return ','.join([
        '"zh-CN":' + q + '中文简体' + q,
        '"en-US":' + q + 'English' + q,
        '"ja-JP":' + q + '日本語' + q,
        '"ru-RU":' + q + 'Русский' + q,
        '"ko-KR":' + q + '한국어' + q,
    ])


def substitui_nomes(texto, q, report):
    """Adiciona pt-BR ao mapa de nomes nativos."""
    corpo = corpo_nomes(q)
    novo = '{' + corpo + ',"pt-BR":' + q + PT_LABEL + q + '}'
    texto, n = re.compile(r'\{' + re.escape(corpo) + r'\}').subn(
        lambda m: novo, texto)
    report['nomes nativos (' + q + ')'] = n
    return texto, n


def substitui_resolver(texto, q, report):
    """Adiciona caso pt ao resolutor de tag de idioma."""
    alvo = (r'case' + q + r'ko' + q + r':return' + q + r'ko\-KR' + q +
            r';default:return' + q + r'en\-US' + q)
    novo = (f'case{q}ko{q}:return{q}ko-KR{q};case{q}pt{q}:return{q}pt-BR{q};'
            f'default:return{q}en-US{q}')
    texto, n = re.subn(alvo, novo.replace('\\', '\\\\'), texto)
    report['resolver de idioma (' + q + ')'] = n
    return texto, n


PADRAO_MAPA_CATALOGO = re.compile(
    r'\{["\']zh\-CN["\']:(\w[\w$]*),"en\-US":(\w[\w$]*),'
    r'"ja\-JP":\{\.\.\.\2,\.\.\.(\w[\w$]*)\},'
    r'"ru\-RU":\{\.\.\.\2,\.\.\.(\w[\w$]*)\},'
    r'"ko\-KR":\{\.\.\.\2,\.\.\.(\w[\w$]*)\}\}')


def substitui_mapa_catalogo(texto, pt_literal):
    """Insere pt-BR no mapa de catalogos do chunk IntlProvider (inline).

    Devolve (texto, numero_de_substituicoes).
    """
    def troca(m):
        en_id = m.group(2)
        return m.group(0)[:-1] + f',"pt-BR":{{...{en_id},...{pt_literal}}}}}'

    return PADRAO_MAPA_CATALOGO.subn(troca, texto)


# ---------------------------------------------------------------------------
# CLI @electron/asar (base russa, MIT)
# ---------------------------------------------------------------------------


def asar_cli():
    exe = shutil.which('npx') or shutil.which('npx.cmd')
    if not exe:
        raise RuntimeError('npx não encontrado no PATH; instale o Node.js')
    return exe


def run_asar(args, cwd):
    cmd = [asar_cli(), '--yes', '@electron/asar'] + args
    proc = subprocess.run(cmd, cwd=cwd, shell=False, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise RuntimeError(f'asar {" ".join(args[:1])} falhou: '
                           f'{proc.stderr.strip()[:500]}')
    return proc.stdout


def read_header(asar_path):
    with open(asar_path, 'rb') as f:
        head = f.read(16)
        json_len = struct.unpack_from('<I', head, 12)[0]
        header_size = struct.unpack_from('<I', head, 4)[0]
        raw = f.read(json_len).decode('utf-8')
        data_start = 8 + header_size
    return json.loads(raw), data_start


def read_entry_bytes(asar_path, header, data_start, *keys):
    node = header['files']
    for i, k in enumerate(keys):
        if i:
            node = node['files']
        node = node[k]
    offset = int(node['offset'], 10)
    size = node['size']
    if offset < 0 or size < 0 or size > 64 * 1024 * 1024:
        raise RuntimeError(f'entrada implausível: offset={offset} size={size}')
    with open(asar_path, 'rb') as f:
        f.seek(data_start + offset)
        return f.read(size)


# ---------------------------------------------------------------------------
# descoberta de arquivos por conteudo
# ---------------------------------------------------------------------------


def varrer_js(raiz):
    for dirpath, _dirnames, filenames in os.walk(raiz):
        for fn in filenames:
            if fn.endswith('.js'):
                yield os.path.join(dirpath, fn)


def ler(caminho):
    with io.open(caminho, encoding='utf-8', errors='surrogateescape') as f:
        return f.read()


def gravar(caminho, texto):
    with io.open(caminho, 'w', encoding='utf-8',
                 errors='surrogateescape', newline='') as f:
        f.write(texto)


def classificar_arquivos(extracted):
    """Devolve (arquivos_locale, arquivos_catalogo) achados por conteudo."""
    locale_files = []
    catalog_files = []
    for path in varrer_js(extracted):
        # pula arquivos gigantes que nao sao bundles do renderer/main
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size > 40 * 1024 * 1024:
            continue
        texto = ler(path)
        tem_array = bool(padrao_array(BT).search(texto) or
                         padrao_array(Q).search(texto))
        tem_mapa = bool(PADRAO_MAPA_CATALOGO.search(texto))
        if tem_mapa:
            catalog_files.append(path)
        if tem_array:
            locale_files.append((path, texto))
    return locale_files, catalog_files


# ---------------------------------------------------------------------------
# syntax check (base russa, MIT; extensao .mjs força parse ESM)
# ---------------------------------------------------------------------------


def syntax_check(chunks, check_dir):
    node = shutil.which('node')
    if not node:
        print('  AVISO: node não encontrado; pulando syntax check')
        return
    for nome, path, texto in chunks:
        alvo = os.path.abspath(os.path.join(check_dir, 'syntax-check.mjs'))
        gravar(alvo, texto)
        proc = subprocess.run([node, '--check', alvo], shell=False,
                              capture_output=True, text=True)
        os.remove(alvo)
        if proc.returncode != 0:
            linhas = (proc.stderr or '').strip().splitlines()
            detalhe = linhas[-2] if len(linhas) >= 2 else proc.stderr[:300]
            raise RuntimeError(f'syntax check FALHOU em {nome}: {detalhe}')
        print(f'  syntax OK: {nome}')


# ---------------------------------------------------------------------------
# fluxo principal
# ---------------------------------------------------------------------------


def find_asar(explicit):
    if explicit:
        return os.path.realpath(explicit)
    home = os.path.expanduser('~')
    candidatos = [
        os.path.join(os.environ.get('LOCALAPPDATA',
                                    os.path.join(home, 'AppData', 'Local')),
                     'Programs', 'ZCode', 'resources', 'app.asar'),
        '/Applications/ZCode.app/Contents/Resources/app.asar',
    ]
    for c in candidatos:
        if os.path.isfile(c):
            return os.path.realpath(c)
    raise RuntimeError('app.asar não encontrado; passe --asar /caminho/app.asar')


def main():
    ap = argparse.ArgumentParser(
        description='Aplica localização pt-BR ao ZCode Desktop')
    ap.add_argument('--asar', help='caminho de resources/app.asar '
                    '(padrão: auto-detectar)')
    ap.add_argument('--catalog', help='caminho do pt-BR-catalog.json '
                    '(padrão: ao lado deste script)')
    ap.add_argument('--dry-run', action='store_true',
                    help='patcheia em memória, não grava nada')
    ap.add_argument('--keep-workdir', action='store_true',
                    help='mantém o diretório temporário de extração')
    args = ap.parse_args()

    asar_path = find_asar(args.asar)
    resources_dir = os.path.dirname(asar_path)
    print(f'Arquivo ZCode: {asar_path}')

    catalog_path = args.catalog or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'translations', 'pt-BR-catalog.json')
    if not os.path.isfile(catalog_path):
        raise RuntimeError(f'catálogo não encontrado: {catalog_path}')
    with io.open(catalog_path, encoding='utf-8') as f:
        pt_catalog = json.load(f)
    print(f'Catálogo pt-BR: {catalog_path} ({len(pt_catalog)} strings)')

    stamp = time.strftime('%Y%m%d-%H%M%S')
    for velho in glob.glob(os.path.join(resources_dir, 'zcode-ptbr-work-*')):
        shutil.rmtree(velho, ignore_errors=True)
    workdir = os.path.join(resources_dir, f'zcode-ptbr-work-{stamp}')
    extracted = os.path.join(workdir, 'tree')
    os.makedirs(extracted, exist_ok=True)

    print('Extraindo com @electron/asar (a 1ª execução pode baixar a ferramenta)...')
    run_asar(['extract', asar_path, extracted], cwd=resources_dir)

    sidecar_root = os.path.join(resources_dir, 'app.asar.unpacked')
    if os.path.isdir(sidecar_root):
        for dirpath, _dirnames, filenames in os.walk(sidecar_root):
            rel = os.path.relpath(dirpath, sidecar_root)
            alvo_dir = extracted if rel == '.' else os.path.join(extracted, rel)
            os.makedirs(alvo_dir, exist_ok=True)
            for fn in filenames:
                shutil.copy2(os.path.join(dirpath, fn),
                             os.path.join(alvo_dir, fn))

    locale_files, catalog_files = classificar_arquivos(extracted)
    print(f'  arquivos com array de locales: {len(locale_files)}')
    for path, _ in locale_files:
        print(f'    - {os.path.relpath(path, extracted)}')
    print(f'  arquivos com mapa de catálogos: {len(catalog_files)}')
    for path in catalog_files:
        print(f'    - {os.path.relpath(path, extracted)}')

    if not catalog_files:
        raise RuntimeError('chunk de catálogo (mapa S) não encontrado — '
                           'instalação ZCode reconhecida?')
    if len(catalog_files) > 1:
        raise RuntimeError(f'esperava 1 mapa de catálogos, achei '
                           f'{len(catalog_files)}')
    if len(locale_files) < 4:
        raise RuntimeError(f'esperava >=4 arquivos com array de locales, '
                           f'achei {len(locale_files)}')

    # idempotência e colisão
    cat_texto = ler(catalog_files[0])
    if PT_LABEL in cat_texto:
        print('Já patcheado — nada a fazer.')
        shutil.rmtree(workdir, ignore_errors=True)
        return 0
    if VAR_PT in cat_texto:
        raise RuntimeError(f'identificador {VAR_PT} colidiria com código existente')

    pt_literal = build_pt_literal(pt_catalog)

    patcheados = []
    print('Patcheando arquivos de locale (array + nomes + resolutor)...')
    for path, texto in locale_files:
        rel = os.path.relpath(path, extracted)
        report = {}
        novo = texto
        for q in (BT, Q):
            novo, _ = substitui_array(novo, q, report)
            novo, _ = substitui_resolver(novo, q, report)
            novo, _ = substitui_nomes(novo, q, report)
        total = sum(v for v in report.values())
        if total == 0:
            print(f'  {rel}: nenhuma edição aplicada (padrões ausentes)')
            continue
        for k, v in report.items():
            if v:
                print(f'  {rel}: {k} = {v}')
        patcheados.append((rel, path, novo))

    print('Patcheando chunk de catálogo (mapa S + catálogo pt inline)...')
    rel_cat = os.path.relpath(catalog_files[0], extracted)
    novo_cat, n_cat = substitui_mapa_catalogo(cat_texto, pt_literal)
    print(f'  {rel_cat}: mapa de catálogos = {n_cat}')
    if n_cat != 1:
        raise RuntimeError('mapa de catálogos não casou exatamente 1 vez')
    patcheados.append((rel_cat, catalog_files[0], novo_cat))

    print('Syntax-check dos arquivos patcheados (node --check, ESM)...')
    syntax_check([(rel, path, texto) for rel, path, texto in patcheados],
                 workdir)

    if args.dry_run:
        shutil.rmtree(workdir, ignore_errors=True)
        print('Dry run OK — nenhum arquivo foi modificado.')
        return 0

    for _rel, path, texto in patcheados:
        gravar(path, texto)

    packed = os.path.join(workdir, 'app.asar.new')
    print('Empacotando com @electron/asar (binários nativos continuam unpacked)...')
    run_asar(['pack', extracted, packed, '--unpack', '**/*.{node,dll,exe}'],
             cwd=resources_dir)

    print('Verificando resultado...')
    header_old, data_old = read_header(asar_path)
    header_new, data_new = read_header(packed)
    problemas = []

    sidecar_old = os.path.join(resources_dir, 'app.asar.unpacked')
    sidecar_new = packed + '.unpacked'

    def sidecar_files(root):
        found = []
        if os.path.isdir(root):
            for dirpath, _dn, filenames in os.walk(root):
                for fn in filenames:
                    found.append(os.path.relpath(os.path.join(dirpath, fn),
                                                 root).replace(os.sep, '/'))
        return sorted(found)

    if sidecar_files(sidecar_old) != sidecar_files(sidecar_new):
        problemas.append('listas de arquivos unpacked diferem')

    pkg_old = read_entry_bytes(asar_path, header_old, data_old, 'package.json')
    pkg_new = read_entry_bytes(packed, header_new, data_new, 'package.json')
    if pkg_old != pkg_new:
        problemas.append('package.json difere após o rebuild')

    cat_new = read_entry_bytes(packed, header_new, data_new,
                               *os.path.relpath(catalog_files[0],
                                                extracted).split(os.sep)
                               ).decode('utf-8', 'ignore')
    if '"pt-BR":{' not in cat_new:
        problemas.append('entrada pt-BR ausente no mapa de catálogos')
    rotulo_encontrado = False
    for _rel, path, _texto in patcheados:
        rel = os.path.relpath(path, extracted)
        novo_conteudo = read_entry_bytes(packed, header_new, data_new,
                                         *rel.split(os.sep)).decode('utf-8',
                                                                    'ignore')
        if ',`pt-BR`' not in novo_conteudo and ',"pt-BR"' not in novo_conteudo:
            problemas.append(f'marcador pt-BR ausente em {rel}')
        if qx(PT_LABEL) in novo_conteudo:
            rotulo_encontrado = True
    if not rotulo_encontrado:
        problemas.append(f'rótulo {PT_LABEL!r} ausente nos arquivos patcheados')

    # prova de fogo: compara byte a byte TODAS as entradas não patcheadas
    # entre o original e o empacotado (o pack pode deduplicar conteúdo
    # idêntico; offsets sobrepostos são válidos se o conteúdo confere).
    def _walk(node, prefixo, out):
        for nome, filho in node.get('files', {}).items():
            cam = prefixo + '/' + nome
            if 'files' in filho:
                _walk(filho, cam, out)
            else:
                out[cam] = filho

    ents_old, ents_new = {}, {}
    _walk(header_old, '', ents_old)
    _walk(header_new, '', ents_new)
    patcheados_rel = {os.path.relpath(p, extracted).replace(os.sep, '/')
                      for _r, p, _t in patcheados}
    f_old = open(asar_path, 'rb')
    f_new = open(packed, 'rb')

    def _ler(f, dstart, e):
        f.seek(dstart + int(e['offset'], 10))
        return f.read(e['size'])

    iguais = diferentes = 0
    try:
        for cam, e_old in ents_old.items():
            e_new = ents_new.get(cam)
            if e_new is None:
                problemas.append(f'entrada ausente no empacotado: {cam}')
                continue
            if cam.lstrip('/') in patcheados_rel:
                continue
            if e_old.get('unpacked') or e_new.get('unpacked'):
                continue
            if _ler(f_old, data_old, e_old) != _ler(f_new, data_new, e_new):
                diferentes += 1
                if diferentes <= 5:
                    problemas.append(f'conteúdo difere do original: {cam}')
            else:
                iguais += 1
    finally:
        f_old.close()
        f_new.close()
    print(f'  comparação byte a byte com o original: {iguais} iguais, '
          f'{diferentes} diferentes')
    if problemas:
        raise RuntimeError('verificação falhou: ' + '; '.join(problemas))

    backup = f'{asar_path}.bak-{stamp}'
    print(f'Criando backup: {backup}')
    shutil.copy2(asar_path, backup)
    print(f'SHA256 do original:')
    subprocess.run(['certutil', '-hashfile', backup, 'SHA256'], shell=False)

    try:
        os.replace(packed, asar_path)
    except PermissionError:
        staged = os.path.join(resources_dir, 'app.asar.novo-ptbr')
        shutil.copy2(packed, staged)
        shutil.rmtree(workdir, ignore_errors=True)
        print()
        print()
        print('O ZCode está rodando e trava o app.asar; o arquivo patcheado')
        print(f'ficou em estágio: {staged}')
        print('Para finalizar: feche o ZCode e rode tool/trocar_apos_fechar.cmd')
        return 2

    if args.keep_workdir:
        print(f'Diretório de trabalho mantido: {workdir}')
    else:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f'Concluído. Arquivo patcheado gravado em {asar_path}')
    print('Reinicie o ZCode e abra Configurações → Geral → Idioma → Português (Brasil).')
    print(f'Para reverter: troque app.asar pelo backup {os.path.basename(backup)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
