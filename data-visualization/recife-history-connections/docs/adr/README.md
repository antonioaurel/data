# Architecture Decision Records (ADR)

Registro das decisões de arquitetura do projeto. Cada decisão relevante vira um arquivo
`NNNN-titulo.md` (numeração sequencial, nunca reescrever histórico — uma decisão que muda
outra cria um **novo** ADR que *supersede* o anterior).

Formato (curto, baseado no modelo de Michael Nygard):

```
# NNNN — Título
Status: Proposto | Aceito | Substituído por ADR-XXXX
Contexto: por que a decisão precisou ser tomada
Decisão: o que foi decidido
Consequências: o que melhora, o que piora, o que fica pendente
```

## Índice

| ADR | Título | Status |
|---|---|---|
| [0001](0001-pipeline-de-dados.md) | Pipeline de dados derivados (graph.json + content.json) | Aceito (modelo de origem substituído pelo 0002) |
| [0002](0002-normalized-graph-model.md) | Normalized graph model (nodes / edges / aliases) as the source | Aceito |

## Decisões ainda a registrar (planejadas)

Discutidas mas ainda não implementadas — viram ADR quando forem feitas:

- **Extrair CSS/JS compartilhado** para `assets/` (hoje tudo é inline e duplicado por página).
- **i18n**: unificar PT/EN numa página só com arquivo de textos, em vez de duas cópias.
- **Migrar `diagram.html` e `stats.html`** para consumir `graph.json`/`content.json`
  diretamente, aposentando o wide CSV gerado (`lista-geral-do-mapeamento.csv`).
