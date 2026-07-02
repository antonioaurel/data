# Data

Hub de projetos de dados — visualização, qualidade e pipelines.

A página inicial (`index.html`) é um menu que lista os projetos e os agrupa por
**abordagem de dados** (Visualização, Qualidade, Pipeline/ETL). Um mesmo projeto
pode aparecer em várias abordagens.

🌐 **Site:** [antonioaurel.github.io/data](https://antonioaurel.github.io/data/)

## Como está organizado

```
Data/
├── index.html          # página-menu (lê projects.json e monta os cards)
├── projects.json       # registro dos projetos + suas abordagens (edite aqui)
├── projects/
│   └── recife-history-connections/   # projeto "Conexões da História"
├── data-source/        # arquivos-fonte de trabalho (ex.: planilha .xlsx local)
├── _archive/           # material antigo/desativado (não publicado)
└── .github/workflows/  # CI: build, deploy e sync da planilha
```

### Como adicionar um novo projeto

1. Coloque a pasta do projeto no repositório.
2. Adicione uma entrada em [`projects.json`](projects.json):

```json
{
  "title": "Nome do Projeto",
  "slug": "nome-do-projeto",
  "path": "caminho/para/o-projeto/",
  "summary": "Uma frase sobre o que ele faz.",
  "approaches": ["visualization", "quality"],
  "tech": ["Python", "D3.js"],
  "status": "live"
}
```

O menu na página inicial se atualiza sozinho — os filtros por abordagem são
gerados a partir dos `approaches` de cada projeto. Para criar uma nova abordagem,
adicione-a também na lista `approaches` do topo do `projects.json`.

### Rodar localmente

```bash
python3 -m http.server 8000
```
Depois abra [http://localhost:8000](http://localhost:8000). Um servidor local é
necessário porque a página carrega `projects.json` via `fetch()`.

## Projetos

| Projeto | Abordagens | Descrição |
|---|---|---|
| [Conexões da História](projects/recife-history-connections/) | Visualização · Qualidade · Pipeline | Grafo interativo das conexões históricas de Recife e Pernambuco |

**Autor:** [Antonio Aureliano](https://conexoesdahistoria.com/)
