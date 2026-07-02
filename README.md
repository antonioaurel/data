# Data

Hub of data projects — visualization, quality, and pipelines.

The landing page (`index.html`) is a menu that lists the projects and groups them by
**data approach** (Visualization, Quality, Pipeline/ETL, Predictive Analysis). The same
project can appear under several approaches.

🌐 **Site:** [antonioaurel.github.io/data](https://antonioaurel.github.io/data/)

## How it's organized

```
Data/
├── index.html          # menu page (reads projects.json and builds the cards)
├── projects.json       # registry of projects + their approaches (edit here)
├── projects/
│   ├── recife-history-connections/    # "Conexões da História"
│   ├── historical-base-cleaning/      # data-quality cleaning of the dataset
│   └── event-attendance-prediction/   # attendance prediction for Facebook events
├── data-source/        # local working source files (e.g. the .xlsx spreadsheet)
├── _archive/           # old / retired material (not published)
└── .github/workflows/  # CI: build, deploy, and Google Sheet sync
```

### Adding a new project

1. Put the project folder in the repository.
2. Add an entry to [`projects.json`](projects.json):

```json
{
  "title": "Project Name",
  "slug": "project-name",
  "path": "projects/project-name/",
  "summary": "One sentence about what it does.",
  "approaches": ["visualization", "quality"],
  "tech": ["Python", "D3.js"],
  "status": "wip"
}
```

The landing page updates itself — the approach filters are generated from each project's
`approaches`. To create a new approach, add it to the `approaches` list at the top of
`projects.json` as well. Use `"status": "live"` or `"wip"` (in progress).

### Run locally

```bash
python3 -m http.server 8000
```
Then open [http://localhost:8000](http://localhost:8000). A local server is required
because the page loads `projects.json` via `fetch()`.

## Projects

| Project | Approaches | Description |
|---|---|---|
| [Conexões da História](projects/recife-history-connections/) | Data Visualization · Quality · Pipeline | Interactive graph of the historical connections of Recife and Pernambuco |
| [Historical Connections — Base Cleaning](projects/historical-base-cleaning/) | Data Quality | Cleaning and validating the dataset (in progress) |
| [Prediction of attendance in Facebook events](projects/event-attendance-prediction/) | Data Prediction | Predicting real attendance at Facebook events (in progress) |

**Author:** [Antonio Aureliano](https://conexoesdahistoria.com/)
