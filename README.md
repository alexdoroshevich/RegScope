# 🔍 RegScope — Federal Register Regulatory Intelligence

> AI-powered analysis of federal regulations and public comments.
> Detect astroturf campaigns. Cluster comment themes. Map regulatory impact.

<!-- ![Demo](docs/demo.gif) -->
<!-- Enable these badges once the repo is public:
[![PR Gate](https://github.com/alexdoroshevich/RegScope/actions/workflows/pr-gate.yml/badge.svg)](https://github.com/alexdoroshevich/RegScope/actions/workflows/pr-gate.yml)
[![CodeQL](https://github.com/alexdoroshevich/RegScope/actions/workflows/codeql.yml/badge.svg)](https://github.com/alexdoroshevich/RegScope/actions/workflows/codeql.yml)
[![Security](https://github.com/alexdoroshevich/RegScope/actions/workflows/security.yml/badge.svg)](https://github.com/alexdoroshevich/RegScope/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
-->

## What it does

RegScope analyzes millions of public comments on federal regulations to:

- **Detect astroturf campaigns** — near-duplicate comments submitted en masse (GAO found 5-30% of comments may be fraudulent)
- **Cluster comments by topic** — semantic grouping using NLP, with AI-generated summaries
- **Map regulatory impact** — which existing rules does a new proposal affect? *(coming soon)*
- **Query regulations in plain English** — ask questions about the Code of Federal Regulations *(coming soon)*

## Quick Start

```bash
# Clone
git clone https://github.com/[you]/regscope.git
cd regscope

# Setup (requires Python 3.13+ and uv)
make setup

# Configure API keys
# Edit .env with your keys (see .env.example)

# Download sample data
make seed

# Start API server
make dev
# → http://localhost:8000/docs
```

## Tech Stack

Python · FastAPI · DuckDB · Polars · sentence-transformers · HDBSCAN · React · TypeScript · Recharts

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Design Decisions

See [docs/DECISIONS.md](docs/DECISIONS.md)

## License

MIT
