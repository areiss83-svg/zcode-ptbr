# ZCode pt-BR 🇧🇷

Tradução **português (Brasil)** para a interface do **ZCode Desktop** (Z.ai), aplicada
como patch local no `app.asar` — com instalador, backup, rollback e re-execução
após atualizações do app.

> Status: catálogo completo (7.803 strings) e patcher provados por comparação
> byte a byte contra o original. Não afiliado à Z.ai; use por sua conta e risco.

## English (short)

Brazilian Portuguese UI translation for **ZCode Desktop**, installed as a local
`app.asar` patch — with installer, timestamped backup, rollback and re-run after
app updates. Full catalog (7,803 strings). Unofficial; not affiliated with Z.ai.
See [Como usar](#como-usar) — commands are the same, just in Portuguese.

## Por que este projeto existe

O ZCode Desktop 3.18+ tem sistema oficial multi-idioma (en, zh, ja, ru, ko) mas
**não tem pt-BR**. Este projeto injeta o catálogo `pt-BR` seguindo o MESMO padrão
oficial usado por ja/ru/ko: fallback automático para inglês nas strings ausentes
(aqui, nenhuma), idioma registrável nos validadores, schemas, resolutor de sistema
e dropdowns de idioma.

O método foi provado pela comunidade: o projeto
[mdn77/zcode-translation-ru](https://github.com/mdn77/zcode-translation-ru) (MIT)
fez isso para o russo antes de o idioma virar oficial na 3.18.0. Este projeto
adapta a técnica deles à arquitetura 3.18.x.

## Como usar

Requisitos: Windows, Python 3.8+, Node.js (npx) no PATH, ZCode Desktop 3.18.x.

```bat
:: 1. Ensaio (não grava nada): extrai, patcheia em memória e faz syntax-check
python tool\aplica_patch.py --dry-run

:: 2. Aplicar (faz backup timestamped antes do swap)
python tool\aplica_patch.py

:: 3. Se o ZCode estava aberto, o arquivo patcheado fica em estágio:
::    feche o ZCode e rode
tool\trocar_apos_fechar.cmd

:: 4. Abra o ZCode: Configurações → Geral → Idioma → Português (Brasil)
```

- **Rollback**: restaure o `app.asar.bak-<carimbo>` gerado na pasta `resources`
  por cima do `app.asar` (com o ZCode fechado).
- **Após atualizar o ZCode**: rode `python tool\aplica_patch.py` de novo — o
  instalador localiza os arquivos por conteúdo (não por nome) e re-verifica tudo.

### Manutenção definitiva (para você reutilizar quando quiser)

O patch **não sobrevive a atualizações do app** por natureza — o instalador
substitui o binário e o update o sobrescreve. A rotina é sempre a mesma e leva
2 minutos:

1. O ZCode atualizou → interface voltou ao inglês? Normal.
2. Feche o ZCode (ou deixe aberto — o instalador coloca em estágio e o
   `trocar_apos_fechar.cmd` conclui).
3. Rode `instalar-ptbr.cmd` (um clique; faz backup novo antes de trocar).
4. Reabra e confira em **Configurações → Geral → Idioma**.

Para levar para outra máquina: copie este repositório (ou clone), instale
Python + Node.js e rode `instalar-ptbr.cmd`. O catálogo e o patcher são
independentes de versão — o instalador se adapta aos arquivos da build
instalada.

## Contribuir

Ajustes nas traduções são bem-vindos: os textos vivem em
`translations/pt/lote-*.json` (e o catálogo fundido em
`translations/pt-BR-catalog.json`). Fluxo sugerido:

1. Edite o lote correspondente (ou mande a correção numa issue/PR).
2. Valide com `python tool\valida_pt.py translations\en-catalog.json
   translations\pt translations\pt-BR-catalog.json` — ele confere chaves,
   placeholders `{nome}` e o balanceamento de plurais ICU.
3. Rode `instalar-ptbr.cmd` e confira na interface.

Melhor ainda: o caminho definitivo é o pt-BR **virar oficial no produto** —
se você também quer isso, comente no PR upstream (link aqui quando aberto).

## O que o instalador faz (segurança)

1. Extrai o `app.asar` com o CLI oficial `@electron/asar`.
2. Encontra os alvos **por conteúdo**: array `SUPPORTED_LOCALES`, mapa de nomes
   nativos, resolutor de tag de idioma (renderer + cópias em main/host/scheduler/
   extension-host) e o mapa de catálogos do chunk `IntlProvider`.
3. Injeta `"pt-BR"` em todos eles e o catálogo pt-BR inline com fallback
   `{...en-US, ...pt-BR}`.
4. `node --check` (ESM) em cada arquivo patcheado.
5. Empacota, **compara byte a byte todas as entradas não-patcheadas contra o
   original**, confere sidecar e `package.json`, cria backup timestamped e só
   então troca.

## Estrutura

```
ACEITE.md                  critérios passa/não-passa do projeto
tool/aplica_patch.py       instalador do patch (dry-run, backup, verificação)
tool/valida_pt.py          valida e funde os lotes (chaves, placeholders, ICU)
tool/extrai_catalogo.py    extrai o catálogo en-US dos fontes TS
tool/divide_lotes.py       divide o catálogo em lotes de tradução
tool/sonda.py, varredura   sondas de leitura do bundle minificado
translations/pt-BR-catalog.json   catálogo final (7.803 chaves)
translations/en|pt/        lotes intermediários
```

## Licenças e créditos

- **Código deste projeto**: MIT (veja `LICENSE`).
- **Técnica de patch**: adaptada de
  [mdn77/zcode-translation-ru](https://github.com/mdn77/zcode-translation-ru) (MIT) —
  obrigado pela base.
- **Strings originais**: [zai-org/ZCode](https://github.com/zai-org/ZCode)
  (Apache-2.0); as traduções aqui são derivadas dessas strings.

**Palavras para busca**: ZCode pt-BR, ZCode português, Z.ai, GLM, GLM Coding
Plan, tradução ZCode, ZCode Desktop em português, Brazilian Portuguese ZCode.
