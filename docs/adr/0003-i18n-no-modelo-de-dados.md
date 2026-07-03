# ADR 0003 — i18n como parte do modelo de dados (PT + EN juntos), sem SQL

- **Status:** Aceita
- **Data:** 2026-07-03
- **Escopo:** Dados de `recife-history-connections`. Respeita o ADR 0001 (**sem banco**).

## Contexto
O conteúdo é bilíngue (PT/EN). A ideia original ("coluna `description_pt`/`description_en`
com uma *view* SQL reportando o que falta") pressupõe banco — que **não teremos** (ADR 0001).
Este ADR adapta a mesma intenção ao mundo sem SQL.

## Situação anterior
- PT vem de `data/nodes.csv` (planilha) → `build.py` → `content.json`.
- EN vem de um arquivo **separado**, `mobile/data-source/descriptions_en.json` (chaveado por id),
  mesclado por um **segundo** `mobile/build/build.py` para dentro de cada `node/*.json` (campo `de`).
- Ou seja: no *runtime* o EN já convive com o PT no `node/*.json`, mas a **fonte** de EN está
  separada da de PT e existem **dois geradores** (build.py duplicado). Não há relatório do que falta.

## Decisão
Tratar as duas línguas como cidadãs de primeira classe no **modelo canônico**, sem SQL:
1. **Fonte única por nó** (meta): PT e EN lado a lado por id (ex.: `content.json` com `d` e `d_en`,
   gerado pelo `build.py`), aposentando o arquivo paralelo como *entrada solta*.
2. **Relatório de cobertura** de EN no build/CI — o equivalente sem-SQL da "view que lista os
   nós sem tradução" (entregue agora em `tools/i18n_report.py`).
3. **Convergir os dois `build.py`** num só gerador de derivados (ver ADR 0002 / gerador único).

## Benefícios
- PT e EN versionados juntos, por id — menos chance de EN "órfão" ou dessincronizado.
- Visibilidade das lacunas (~50 nós sem EN) via relatório, sem precisar de banco.
- Caminho para um único gerador (fim do build.py duplicado).

## Pontos de atenção
- A **planilha** é a fonte de PT e não tem coluna de EN hoje; consolidar 100% na origem exige
  ou (a) adicionar EN à planilha, ou (b) manter `descriptions_en.json` como co-fonte formal por id
  e o build mesclar — decisão do mantenedor.
- Mexer no pipeline de build é sensível (alimenta o deploy) — fazer incremental e com `--check`.

## Melhora esperada
Uma origem clara e reportável para i18n, base para unificar os geradores, e um alarme de
cobertura que impede regressões silenciosas de tradução.
