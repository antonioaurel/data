# 0001 — Pipeline de dados derivados (graph.json + content.json)

**Status:** Aceito · 2026-06-30

## Contexto

O site (matrix, diagrama, stats) carregava o `data/lista-geral-do-mapeamento.csv` inteiro
(~812 KB, 24 colunas) e só desenhava depois de baixar e parsear tudo. Medições:

- `Dados consolidados` (47%) e `Fonte da descrição` (6%) **nunca são usadas** pelas páginas —
  a primeira é só uma cópia denormalizada do que já existe em outras colunas; a segunda é uma
  URL idêntica repetida nas 497 linhas.
- `Descrição` (35%) só é usada no painel de detalhe, ao clicar num nó.
- Para *desenhar* o grafo bastam nome + tipo + arestas (~32 KB).
- A `matrix` carregava a biblioteca **d3** inteira só para usar `d3.csv` (parser de CSV).
- Os arquivos derivados eram gerados por scripts avulsos, não versionados (risco de drift).
- A base **vai ser expandida**, então o processo precisa ser reproduzível e validado.

## Decisão

1. **Fonte da verdade** continua sendo `data/lista-geral-do-mapeamento.csv` (export do Sheets).
2. Um **`build.py` versionado** lê o CSV, **valida** e gera dois arquivos derivados:
   - `data/graph.json` (~32 KB) — nós (nome + tipo) + arestas; suficiente para renderizar.
   - `data/content.json` (~344 KB) — descrição/local/imagem por nó; carregado **sob demanda**.
3. A **matrix** passa a usar `fetch` + `JSON` (sem d3): baixa o `graph.json` e desenha; o
   `content.json` carrega em segundo plano e só alimenta o painel de detalhe.
4. **CI** (`.github/workflows/build.yml`) roda `build.py --check` em todo push: falha se os
   JSON commitados estiverem fora de sincronia com o CSV.
5. Arquivos sem uso (`matrix.csv` antigo, dumps de export) movidos para `../../Depreciated/`
   (fora da pasta publicada), preservados via `git mv`.

## Consequências

**Melhora**
- *First paint* da matrix cai de ~812 KB → ~32 KB (−96%); o texto pesado carrega depois.
- Matrix deixa de depender do d3 (−~73 KB e um request bloqueante a um domínio externo).
- Geração de dados vira **um comando reproduzível e validado**; a CI impede que o site
  publicado divirja da base — importante com a base crescendo.
- Nenhuma mudança visual; a fonte da verdade (CSV completo) fica intacta.

**Pendências / custo**
- Passam a existir **arquivos derivados commitados**: ao editar o CSV é preciso rodar
  `python3 build.py` e commitar os JSON (a CI cobra isso).
- O **diagrama** ainda carrega o CSV completo via d3 (usa mais campos) — migração futura.
- O limite de **15 colunas de interconexão** (grau ≤ 15) continua; com a expansão da base,
  considerar uma lista de arestas explícita (ADR futuro).
- A duplicação de código **inline** e **PT/EN** por página permanece (ADR futuro: assets/ + i18n).
