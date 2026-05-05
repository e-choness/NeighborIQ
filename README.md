# NeighborIQ

**NeighborIQ** is an open-source AI-driven platform for neighborhood insights and community-driven data analysis. Built with Python and designed for extensibility, it leverages modern LLM capabilities to provide actionable intelligence at the local level.

---

## 🚀 Quick Start

### Install

Ensure you have Python 3.10+ and Docker installed.

**Bash**

```
# Clone the repository
git clone https://github.com/e-choness/NeighborIQ.git
cd NeighborIQ

# Start the environment via Docker
docker-compose up -d
```

### Fastest Setup

NeighborIQ is pre-configured for rapid deployment. To run migrations and initialize the service:

**Bash**

```
# Run database migrations
python -m migrations.apply

# Start the AI Insight service
python -m services.ai_insight.main
```

---

## 🛠️ Features

NeighborIQ is built for modularity and intelligence. It moves beyond simple data storage into active community reasoning.

* **Any Model, One Service** — Integration-ready for OpenAI, Gemini, and local providers via a unified service layer.
* **AI Insight Engine** — Dedicated services for generating neighborhood-specific intelligence and data patterns.
* **Shared Core Library** — Robust shared logic and utilities to ensure consistency across microservices.
* **Dockerized Workflow** — Fully containerized architecture for seamless local development and cloud scaling.
* **Developer Friendly** — Clean code standards enforced with `black` and comprehensive test suites.

---

## 📁 Repository Structure

| **Directory**              | **Description**                                              |
| -------------------------------- | ------------------------------------------------------------------ |
| **`services/`**          | Core business logic, including the AI Insight service.             |
| **`shared/`**            | Common utilities, schemas, and shared models used across services. |
| **`migrations/`**        | Database schema evolution and version control.                     |
| **`docker-compose.yml`** | Orchestration for the database, services, and local environment.   |

---

## 🏗️ Development

### Testing

We prioritize reliability. Run the test suite for the AI Insight service using:

**Bash**

```
pytest services/ai_insight/tests
```

### Modernization Plan

The project is currently undergoing active development. Refer to [MODERNIZATION_PLAN.md](MODERNIZATION_PLAN.md) for the roadmap, including upcoming architectural changes and feature milestones.

### Style Guide

This project uses [Black](https://www.google.com/search?q=https://github.com/psf/black) for code formatting. Please ensure all contributions are formatted:

**Bash**

```
black .
```

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
