# Goalcast

Personal football data analysis tool powered by [OddAlert](https://oddalerts.com). Fetches real-time odds, dropping odds, and trends — served via a dark-themed dashboard.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2
- An OddAlert API key

## Quick start

**1. Create `backend/.env`:**

```
ODDALERTS_API_KEY=your_key_here
```

**2. Build and start:**

```bash
./start.sh start --build
```

**3. Open [http://localhost](http://localhost)**

Data syncs automatically in the background. Select leagues on the Matches page to start seeing match cards.

---

## Commands

| Command | Description |
|---------|-------------|
| `./start.sh start --build` | Build images and start all services |
| `./start.sh start` | Start without rebuilding |
| `./start.sh stop` | Stop all services |
| `./start.sh logs` | Follow logs from all services |
| `./start.sh build` | Build images only |

## Data persistence

Both files live on the host and are mounted read/write into the backend container — nothing is baked into the image.

| Host path | Container path | Description |
|-----------|---------------|-------------|
| `backend/.env` | `/app/.env` (read-only) | API key |
| `backend/data/` | `/app/data/` | SQLite database |

## Development (without Docker)

```bash
# Backend
cd backend
.venv/bin/uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm run dev
# → http://localhost:5173
```
