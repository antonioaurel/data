# recife-tests — Arquitetura

Projeto de testes **central e standalone** para o trabalho de _Conexões da
História / Recife_. Reúne, num só lugar, as três naturezas de teste do produto:
**API**, **dados (db)** e **UI (telas)**.

> Contexto: até então o repositório tinha apenas uma suíte de API acoplada ao
> projeto `connections-api`. Este projeto extrai essa suíte e passa a ser o
> ponto único onde os testes vivem, evoluem e rodam.

---

## 1. Estrutura

```
projects/recife-tests/
├── package.json            # deps + scripts (Node/Playwright)
├── playwright.config.js    # config da suíte de API (sobe o servidor sozinho)
├── README.md               # como rodar
├── docs/
│   └── ARCHITECTURE.md     # este documento
└── tests/
    ├── api/                # ✅ pronto — REST API (Playwright request, sem browser)
    │   └── items.spec.js
    ├── db/                 # ⏳ planejado — validação dos CSVs (pytest)
    │   └── .gitkeep
    └── ui/                 # ⏳ planejado — telas via data-testid (Playwright browser)
        ├── .gitkeep
        └── component-ids.xlsx   # catálogo dos data-testid (pc-<screen>-...)
```

As três pastas são **isoladas por natureza**, porque cada uma tem runtime e
dependências diferentes (ver §5).

---

## 2. Suíte de API (pronta)

- **O que cobre:** o CRUD REST exposto pelo projeto `connections-api` sobre o
  dataset `nodes.csv` (health, listagem com paginação/filtro/busca, GET por id,
  POST/PUT/PATCH/DELETE, `_reset` e regressões). São **23 testes**.
- **Como testa:** Playwright com o **`request` context** — cliente HTTP puro,
  **sem browser**. Bate direto nos endpoints.
- **Isolamento:** store em memória compartilhado → `workers: 1`, serial, e um
  `POST /api/_reset` no `beforeEach` restaura o dataset entre testes.

### Dependência cruzada com `connections-api`

O servidor testado **não vive aqui** — vive em `projects/connections-api/src/`.
O `playwright.config.js` sobe esse servidor automaticamente antes dos testes:

```js
webServer: {
  command: 'node src/server.js',
  cwd: path.resolve(__dirname, '../connections-api'), // resolve o express de lá
  url: `${baseURL}/health`,   // espera o /health responder 200 antes de testar
  reuseExistingServer: !process.env.CI,
}
```

Consequência arquitetural: **acoplamento por caminho relativo** entre
`recife-tests` e `connections-api`. É o custo de manter o servidor (produto) e os
testes (qualidade) em projetos separados. O `/health` funciona como "porteiro":
os testes só começam quando o serviço está no ar e com os dados carregados.

```
┌──────────────────┐   sobe (webServer)   ┌───────────────────────┐
│   recife-tests   │ ───────────────────► │   connections-api     │
│  (Playwright)    │   HTTP :3100         │  Express + nodes.csv  │
│  tests/api/*.js  │ ◄─────────────────── │  (in-memory store)    │
└──────────────────┘   respostas JSON     └───────────────────────┘
```

---

## 3. Suíte de dados / db (planejada)

Validação sobre os CSVs-fonte em `../recife-history-connections/data/`
(`nodes.csv`, `edges.csv`, `coords.csv`, `periods.csv`, `aliases.csv`):

- ids únicos e bem-formados; sem órfãos;
- `edges` referenciando apenas nós existentes;
- coordenadas finitas ou vazias (nunca `Infinity`/`NaN`);
- `type`/`sub_type` dentro do vocabulário esperado;
- espelhamento com a planilha-fonte quando aplicável.

**Runtime previsto:** `pytest` (o projeto já é Python — `build.py`,
`build_map.py`), lendo os CSVs diretamente (sem servidor).

---

## 4. Suíte de UI (planejada)

Testes de tela (Diagrama/Grafo, Mapa, Lista, Matriz) dirigindo o site publicado
via os hooks `data-testid` no padrão `pc-<screen>-<region>-<component>`
introduzidos pela PR #27.

- **Fonte da verdade dos seletores:** `tests/ui/component-ids.xlsx` — catálogo
  Subsystem · Module · Functionality · Component · Type · **Component ID**.
- **Runtime previsto:** Playwright com **browser real**, contra o site servido
  (estático) de `recife-history-connections`.

---

## 5. Runtimes e dependências

| Suíte | Runtime | Depende de | Estado |
|---|---|---|---|
| api | Node + Playwright (`request`) | servidor de `connections-api` | ✅ |
| db  | Python + pytest | CSVs de `recife-history-connections/data/` | ⏳ |
| ui  | Node + Playwright (browser) | site servido + `component-ids.xlsx` | ⏳ |

Nota: por misturar **dois runtimes** (Node e Python), não há um único
`npm test` que rode tudo. Cada suíte tem seu comando; um orquestrador
(Makefile / script / CI) pode uni-las mais tarde.

---

## 6. Como rodar

```sh
# API (pronta)
cd projects/connections-api && npm install   # uma vez (express p/ o servidor)
cd projects/recife-tests && npm install        # uma vez (@playwright/test)
npm test          # sobe o servidor na :3100 e roda os 23 testes
npm run test:api  # só a API
```

---

## 7. Princípios de design

1. **Testes separados do produto.** Qualidade evolui sem inchar os projetos de
   produto (`connections-api`, `recife-history-connections`).
2. **Um lugar só.** Toda suíte (api/db/ui) descobrível num único projeto.
3. **Isolamento por natureza.** Cada tipo de teste com seu runtime, sem forçar
   uma stack única.
4. **Auto-suficiente ao rodar.** A suíte sobe o que precisa (servidor) e espera
   o `/health` — sem passo manual.
5. **Fonte da verdade explícita.** IDs de UI num catálogo versionado
   (`component-ids.xlsx`), não espalhados pelo código de teste.
