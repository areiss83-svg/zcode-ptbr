# ACEITE — Tradução pt-BR do ZCode Desktop (patch local)

Versão alvo: ZCode Desktop 3.18.2.10443 (app.asar de 2026-11-12). Escopo escolhido
pelo dono: **só desktop** (2026-11-13). Base comunitária: `mdn77/zcode-translation-ru`
(MIT), adaptada para a 3.18.x.

## Critérios passa/não-passa

1. **App abre**: ZCode 3.18.2 abre e renderiza normalmente após o patch, sem tela
   de erro crítico. Prova: abertura observada após o swap.
2. **Idioma selecionável**: "Português (Brasil)" aparece no seletor de idioma das
   configurações e pode ser escolhido. Prova: verificado na UI.
3. **Strings em PT**: com pt-BR ativo, áreas centrais (menus, configurações, chat)
   aparecem em português; o que não foi traduzido cai em inglês (fallback oficial),
   nunca chave crua. Prova: amostra de telas pós-patch.
4. **Reversão provada**: backup timestamped do app.asar original + SHA256
   registrado; restore devolve o app original funcional. Prova: checksums antes/depois.
5. **Persistência**: fechar e abrir o app mantém pt-BR ativo (setting.json válido,
   sem reset silencioso para en-US). Prova: ciclo de reinício observado.

## Riscos e freios

- Patch em binário do app (app.asar 384 MB): dry-run obrigatório antes do swap;
  backup antes de substituir; rollback testado no critério 4.
- Update do app desfaz o patch → re-run do instalador (localiza chunks por
  conteúdo, não por nome).
- `X-Client-Language` passa a enviar `pt-BR` aos endpoints da Z.ai (campo
  informativo; risco baixo, registrado aqui).
- Bancada indisponível nesta sessão (provedores dos agentes fora da conta atual,
  conferido por lista de modelos): construção e revisão seguem direto no chat,
  com verificação por caminho próprio em cada passo.

## Entrega

Recibo critério a critério com a prova de cada um. Achado sem quebra de aceite
vai para backlog, não reabre o trabalho.
