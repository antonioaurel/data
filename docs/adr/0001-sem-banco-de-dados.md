# ADR 0001 — Sem banco de dados: JSON estático gerado a partir de uma planilha

- **Status:** Aceita
- **Data:** 2026-07-03
- **Escopo:** O site público (o hub "Data" e `recife-history-connections`). Não vincula
  serviços futuros implantados separadamente (ver "Quando revisitar").

## Contexto
Site **estático no GitHub Pages** — não há runtime de servidor nem onde rodar consultas.
O dataset é pequeno e curado (~556 nós, ~3,8k arestas) e é **somente leitura** em runtime.

## Situação anterior
A cogitação de um banco (SQLite/Postgres) surgiu porque o projeto "está ficando grande".
Hoje a fonte de verdade é uma **planilha Google** (abas nodes/edges/aliases) → `pull_sheet.py`
baixa para `data/*.csv` (versionado no git) → `build.py` valida e gera os JSON que o site
consome. A integridade é garantida **no build** (falha em id/nome duplicado, origem não
resolvida) e por um **drift-check diário** no CI.

## Decisão
**Não introduzir banco de dados no site.** A fonte canônica continua planilha → CSV
versionado → JSON gerado. O frontend estático consome apenas JSON.

## Benefícios
- **Zero infraestrutura e custo** — nada para hospedar, manter ou pagar.
- **Build reprodutível** e diffável (CSV no git + `build.py` só com stdlib).
- **Histórico completo** dos dados no git.
- **Superfície de edição amigável** (planilha) para um mantenedor não-desenvolvedor.
- **Modelo mental simples** — sem camada de banco para operar.

## Pontos de atenção
- Sem consulta ad-hoc em runtime (tudo é pré-computado).
- Validação é Python no build, não constraints do banco (FK/unique/enum).
- A edição é uma planilha, não um store tipado.

## Melhora esperada
Nenhuma mudança de comportamento — a decisão **evita** custo e complexidade que não trariam
benefício a uma visualização somente-leitura. Mantém o pipeline atual, já reprodutível.

## Quando revisitar
- Se entrar uma **camada de API/serviços** (runtime dinâmico, escrita, auth): seria um
  **projeto separado**, com o próprio banco (ex.: Postgres atrás de uma API) e o próprio ADR.
- Se o dataset crescer além do que o JSON estático serve bem, ou o cliente precisar de
  consulta real: avaliar **SQLite como fonte em build-time** (ainda exportando os mesmos JSON)
  ou **SQLite no browser (sql.js)** antes de qualquer banco em servidor.
