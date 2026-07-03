# ADR 0002 — Unificar a camada compartilhada (dados/i18n/tokens), não a página

- **Status:** Aceita
- **Data:** 2026-07-03
- **Escopo:** Frontend de `recife-history-connections` (desktop `pages/` + `mobile/site/`).

## Contexto
Existem duas frentes de UI: **desktop** (`pages/`, D3 + Leaflet) e **mobile** (`mobile/site/`,
`app.js`/`app.css` self-contained, canvas/SVG), com **roteamento por viewport** (redirect em
1024px). Isso gera duplicação e foi a raiz de vários atritos ao iterar os mocks.

## Situação anterior
Cada frente carrega os dados, traduz (i18n) e define cores/tokens **por conta própria**:
duas implementações de diagrama, duas de mapa, dicionários i18n paralelos e paletas repetidas.
Mudar uma cor ou uma string exige tocar em dois lugares.

## Decisão
Unificar **a camada compartilhada**, mantendo a **apresentação separada por formato**:
- **Dados:** um módulo único de carregamento/normalização do grafo (nós, arestas, adjacência).
- **i18n:** um único dicionário/serviço PT/EN consumido por ambas as frentes.
- **Tokens de design:** uma fonte única de cores por tipo/categoria e demais tokens.
- (Opcional, depois) um *core* de renderização do grafo reutilizável.

**Explicitamente NÃO** unificar tudo numa única página responsiva monolítica.

## Benefícios
- Remove a duplicação de dados/i18n/cores (fonte única → sem divergência).
- Corrige a raiz dos atritos dos mocks (as duas frentes deixam de "brigar").
- Mudanças de string/cor/modelo passam a ser feitas **em um só lugar**.

## Pontos de atenção
- Forçar "uma única página" **concentraria** complexidade (um componente gigante com muitos
  breakpoints) — por isso a decisão é unificar a *camada*, não a *página*.
- Exige definir uma fronteira clara entre "compartilhado" e "específico de formato".
- Refatoração incremental para não quebrar o site publicado.

## Melhora esperada
Menos código duplicado, consistência garantida entre desktop e mobile (mesmas cores, mesmas
traduções, mesmo modelo de dados) e manutenção mais barata — sem o risco de uma reescrita
monolítica.
