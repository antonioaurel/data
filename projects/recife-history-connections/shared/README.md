# shared/ — camada compartilhada (ADR 0002)

Fonte única de verdade para o que **desktop** (`pages/`) e **mobile** (`mobile/site/`)
compartilham, para acabar com a duplicação (cores repetidas, dicionários paralelos).

## O que já existe
- **`tokens.json`** — cores canônicas por **tipo** (local/personagem/evento/other) e por
  **categoria** (as 15). Edite aqui.
- **`build_shared.py`** — gera `tokens.css` a partir do `tokens.json`.
  - `python3 shared/build_shared.py` → (re)gera `tokens.css`
  - `python3 shared/build_shared.py --check` → falha se estiver dessincronizado (para o CI)
- **`tokens.css`** — **gerado** (não editar à mão): expõe `--type-*` e `--cat-*`.

## Como consumir
Cada frontend faz `<link rel="stylesheet" href=".../shared/tokens.css">` e usa
`var(--type-local)`, `var(--cat-igreja)`, … em vez de hardcodar hex. Assim uma cor muda em
**um lugar só**.

## Migração (incremental, próximos passos)
1. Ligar `tokens.css` no mobile (`app.css`) e no desktop (`pages/*.html`) e trocar os hex
   pelas variáveis. Feito por página, sem big-bang.
2. Extrair o **dicionário i18n** (strings PT/EN de navegação/labels) para `shared/i18n.json`
   e um pequeno módulo que ambas as frentes consomem (hoje vive dentro do `app.js`).
3. Extrair o **modelo de dados do grafo** (carregamento/adjacência) para um módulo comum.

Ver `docs/adr/0002-unificar-a-camada-nao-a-pagina.md` e `0003-i18n-no-modelo-de-dados.md`.
