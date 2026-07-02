# 0003 — Aposentar o wide CSV (`lista-geral-do-mapeamento.csv`)

Status: Aceito

## Contexto

O modelo normalizado (nodes/edges/aliases → `graph.json` + `content.json`, ADR-0002) já era
a fonte. Mas o `build.py` ainda **gerava** um CSV largo herdado
(`lista-geral-do-mapeamento.csv`, 6 campos + `Interconexão 1..15`) só porque duas páginas
ainda o liam diretamente: `diagram.html` e `stats.html`. Isso mantinha um terceiro artefato
derivado (~400 KB) no repositório, versionado e checado pelo CI, sem ninguém editá-lo à mão.

## Decisão

Migrar as páginas restantes para consumir `graph.json` + `content.json` e **remover** o wide
CSV do projeto:

- `diagram.html` (pt/en): passou a montar nós/arestas a partir dos dois JSON (feito na migração
  do diagrama).
- `stats.html` (pt/en): reconstrói localmente a "linha larga" (6 campos + `Interconexão 1..15`,
  vizinhos ordenados e truncados em 15 — mesma lógica que o `build.py` usava) a partir dos JSON,
  preservando exatamente os mesmos *fill rates* e listas de problemas.
- `build.py`: removida a geração de `lista-geral-do-mapeamento.csv` (`wide_csv_text`, `WIDE_OUT`,
  `WIDE_HEADER`) e a sua verificação no modo `--check`.
- Arquivo `data/lista-geral-do-mapeamento.csv` deletado do repositório.

## Consequências

- **Melhora:** uma única representação derivada (os dois JSON); menos ~400 KB versionados; o CI
  não precisa mais manter um terceiro artefato em sincronia; `build.py` mais simples.
- **Melhora:** todas as páginas agora leem exatamente a mesma fonte, sem risco de divergência
  entre o CSV largo e os JSON.
- **Piora / atenção:** quem tenha ferramentas externas apontando para o wide CSV precisa passar a
  ler os JSON (ou o próprio Sheet). O formato "uma linha por nó com 15 colunas de conexão" deixa
  de existir como artefato pronto.
