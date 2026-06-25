# Conexões da História

An interactive D3.js force-directed diagram mapping the historical connections between people, places, and events that shaped **Recife and Pernambuco, Brazil**.

Discover how seemingly unrelated locations, historical figures, and events are deeply linked across time — from the Dutch-Portuguese wars to the 1930 Brazilian Revolution and beyond.

🌐 **Live site:** [antonioaurel.github.io/data/data-visualization/recife-history-connections](https://antonioaurel.github.io/data/data-visualization/recife-history-connections/)  
🗺️ **Main project:** [conexoesdahistoria.com](https://conexoesdahistoria.com)

---

## What it contains

The diagram visualises three categories of nodes:

| Category | Description |
|---|---|
| **Location** | Historical locations in Recife and Pernambuco |
| **Historical Figure** | Politicians, writers, engineers, activists |
| **Historical Event** | Events and movements that shaped the region |

Nodes are connected by edges representing documented historical relationships. Node size reflects how many connections each entry has.

---

## How to run locally

This is a static HTML project — no build step required.

**Option 1 — Python (recommended):**
```bash
cd data-visualization/recife-history-connections
python3 -m http.server 8000
```
Then open [http://localhost:8000](http://localhost:8000) in your browser.

> A local server is required because the diagram loads `lista-geral-do-mapeamento.csv` via `d3.csv()`, which browsers block when opening files directly (`file://`).

**Option 2 — Node.js:**
```bash
npx serve .
```

**Option 3 — VS Code:**  
Install the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension, right-click `index.html` → *Open with Live Server*.

---

## How to use the diagram

- **Zoom** — scroll wheel or pinch to zoom in/out
- **Pan** — click and drag the background
- **Move nodes** — click and drag any node
- **Inspect** — click a node to see its description and connections in the right panel
- **Navigate** — click a connection card in the panel to jump to that node

---

## Data

All data lives in `lista-geral-do-mapeamento.csv`. Columns:

| Column | Description |
|---|---|
| Name | Name of the entry |
| Type | Category (Location / Historical Figure / Historical Event) |
| Sub-Type | Subcategory |
| Location | Neighbourhood or area in Recife |
| Image | Image URL |
| Description | Historical description |
| Connection 1–15 | Names of connected entries |

---

## Authors

**Antonio Aureliano** — computer engineer and Olinda enthusiast, creator of the Conexões da História project.

- 🌐 [conexoesdahistoria.com](https://conexoesdahistoria.com)
- 📸 Instagram: [@conexoesdahistoria](https://instagram.com/conexoesdahistoria)
- 💼 [LinkedIn](https://linkedin.com/in/antonioaurel)

**Manuela Barbosa** — initial page implementation.

---

## Tech stack

- [D3.js v4](https://d3js.org/) — force-directed graph
- Vanilla HTML/CSS/JS — no framework dependencies
- GitHub Pages — hosting

---

## Technology upgrade paths

The sections below describe how to migrate or extend this project using more powerful tools.

---

### D3.js v7 (upgrade from v4)

**What it adds:** Modern ES modules, better TypeScript support, cleaner API, active maintenance. The force simulation API is largely the same so migration is low-risk.

**How to use:**

1. Replace the script tag:
```html
<!-- remove -->
<script src="https://d3js.org/d3.v4.min.js"></script>

<!-- add -->
<script src="https://d3js.org/d3.v7.min.js"></script>
```

2. Update event syntax — v7 replaced `d3.event` with the event passed directly to handlers:
```js
// v4
.on("zoom", function() { g.attr("transform", d3.event.transform); })

// v7
.on("zoom", (event) => { g.attr("transform", event.transform); })
```

3. Update drag handlers the same way:
```js
// v4
.on("start", function(d) { d.fx = d3.event.x; })

// v7
.on("start", (event, d) => { d.fx = event.x; })
```

4. `d3.csv` now returns a Promise instead of using a callback:
```js
// v4
d3.csv("file.csv", function(error, data) { ... })

// v7
d3.csv("file.csv").then(function(data) { ... })
```

---

### Sigma.js + Graphology

**What it adds:** WebGL rendering that handles thousands of nodes smoothly. Graphology is the underlying graph data structure; Sigma.js renders it. Best choice if the dataset grows significantly.

**How to use:**

1. Install via npm:
```bash
npm install sigma graphology graphology-layout-forceatlas2
```

2. Load your CSV, build the graph, and render:
```js
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";

const graph = new Graph();

// Add nodes from CSV
data.forEach(row => {
  graph.addNode(row.Nome, {
    label: row.Nome,
    size: 5,
    color: row.Tipo === "Local" ? "#4a90d9" : "#e8833a",
    x: Math.random(), y: Math.random()
  });
});

// Add edges
links.forEach(link => {
  if (graph.hasNode(link.source) && graph.hasNode(link.target)) {
    graph.addEdge(link.source, link.target);
  }
});

// Run layout
forceAtlas2.assign(graph, { iterations: 150 });

// Render
const renderer = new Sigma(graph, document.getElementById("container"));
```

3. Listen for node clicks:
```js
renderer.on("clickNode", ({ node }) => {
  const attrs = graph.getNodeAttributes(node);
  showDetail(attrs);
});
```

---

### Cytoscape.js

**What it adds:** Rich built-in layouts (hierarchical, circular, breadth-first, cola), filtering, export to PNG/JSON, and a large plugin ecosystem. Good for structured historical timelines.

**How to use:**

1. Add via CDN:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
```

2. Build elements from the CSV and render:
```js
const elements = [];

// Nodes
data.forEach(row => {
  elements.push({
    data: { id: row.Nome, label: row.Nome, tipo: row.Tipo, img: row.Imagem, desc: row["Descrição"] }
  });
});

// Edges
links.forEach(link => {
  elements.push({
    data: { source: link.source, target: link.target }
  });
});

const cy = cytoscape({
  container: document.getElementById("cy"),
  elements,
  style: [
    { selector: "node", style: { label: "data(label)", "font-size": 10 } },
    { selector: "node[tipo='Local']",      style: { "background-color": "#4a90d9" } },
    { selector: "node[tipo='Personagem']", style: { "background-color": "#e8833a" } },
    { selector: "edge", style: { "line-color": "#333", width: 1 } }
  ],
  layout: { name: "cose" } // force-directed; try "breadthfirst" or "circle"
});

// Click to inspect
cy.on("tap", "node", evt => {
  const node = evt.target.data();
  showDetail(node);
});
```

3. Available layouts: `cose`, `breadthfirst`, `circle`, `grid`, `concentric`, `dagre` (requires plugin).

---

### Observable / ObservableHQ

**What it adds:** A browser-based notebook where each cell is reactive — changing data automatically updates the diagram. Great for sharing explorable versions of the project without a server.

**How to use:**

1. Go to [observablehq.com](https://observablehq.com) and create a free account.

2. Create a new notebook and import the CSV as a file attachment.

3. Use the built-in D3 cell pattern:
```js
// Cell 1 — load data
data = FileAttachment("lista-geral-do-mapeamento.csv").csv()

// Cell 2 — build links
links = data.flatMap(row =>
  Object.entries(row)
    .filter(([k, v]) => k.startsWith("Intercon") && v !== "")
    .map(([_, v]) => ({ source: row.Nome, target: v }))
)

// Cell 3 — render
chart = {
  const svg = d3.create("svg").attr("viewBox", [0, 0, width, 600]);
  // ... force simulation as normal
  return svg.node();
}
```

4. Share the notebook URL — anyone can view, fork, and remix it.

---

### Neo4j Bloom (graph database)

**What it adds:** A dedicated graph database that stores nodes and relationships natively. Neo4j Bloom is a visual explorer on top of it — fast full-text search, path finding, and filtering across the entire dataset. Best for the long-term if the project scales to thousands of entries.

**How to use:**

1. Download [Neo4j Desktop](https://neo4j.com/download/) (free for local use) and create a new database.

2. Import the CSV using the Cypher query language:
```cypher
// Load nodes
LOAD CSV WITH HEADERS FROM 'file:///lista-geral-do-mapeamento.csv' AS row
MERGE (n:Entrada {nome: row.Nome})
SET n.tipo = row.Tipo, n.descricao = row.Descricao, n.imagem = row.Imagem, n.local = row.Local;

// Load relationships (repeat for Interconexão 2 through 15)
LOAD CSV WITH HEADERS FROM 'file:///lista-geral-do-mapeamento.csv' AS row
WITH row WHERE row.`Interconexão 1` <> ''
MATCH (a:Entrada {nome: row.Nome}), (b:Entrada {nome: row.`Interconexão 1`})
MERGE (a)-[:CONECTADO_A]->(b);
```

3. Open **Neo4j Bloom** from the desktop app to visually explore the graph with search and filters — no code needed.

4. For a web-embeddable version, use the [Neo4j JavaScript driver](https://neo4j.com/developer/javascript/):
```js
import neo4j from "neo4j-driver";
const driver = neo4j.driver("bolt://localhost:7687", neo4j.auth.basic("neo4j", "password"));
const session = driver.session();
const result = await session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 200");
// feed result.records into D3 or Sigma.js
```

---

### Obsidian (knowledge graph — no code)

**What it adds:** Obsidian is a markdown note-taking app with a built-in **Graph View** that automatically generates a force-directed connection map identical to this project — but maintained through writing notes, not editing CSVs.

**How to use:**

1. Download [Obsidian](https://obsidian.md) (free).
2. Create a vault (folder) with one `.md` file per entry (e.g. `Ariano Suassuna.md`).
3. Link notes using `[[double brackets]]`:
```markdown
# Ariano Suassuna
Playwright from Pernambuco. Created [[Auto da Compadecida]].
Secretary of Culture under [[Eduardo Campos]] government.
Linked to [[Academia Pernambucana de Letras]].
```
4. Open **Graph View** (Ctrl+G) to see the full interactive map, colour-coded by folder or tag.
5. Use the **Dataview** plugin to query entries by tipo, local, or era — similar to a database.

To migrate the existing CSV to Obsidian, each row becomes one note and each `Interconexão` column becomes a `[[wikilink]]` in the note body.
