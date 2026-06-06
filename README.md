# NexusDesk — Agentic AI for Enterprise IT Support

An intelligent multi-agent IT service desk that automates ticket resolution using NLP, RAG, and risk-aware decision-making. It handles routine requests autonomously, resets passwords across integrated applications, and escalates complex issues to human agents.

---

## Prerequisites

Install these before running:

| Tool | Version | Download |
|---|---|---|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| MongoDB | 7+ | https://mongodb.com/try/download/community |
| Tesseract OCR | Latest | https://github.com/UB-Mannheim/tesseract/wiki (Windows) |
| Git | Any | https://git-scm.com |

---

## Project Structure

```
Unisys/
├── backend/          ← FastAPI AI backend (port 8000)
├── client/           ← React frontend (port 3000)
├── Web_Auth/         ← Flask demo auth app (port 5000)
├── env/              ← Python venv for backend (created by you)
└── Insturctions.txt  ← Original project brief
```

---

## Setup & Run

### 1. Clone the repo

```bash
git clone https://github.com/antonyronlado/Agentic-AI-for-Enterprise-IT-Support.git
cd Agentic-AI-for-Enterprise-IT-Support
```

### 2. Start MongoDB

Make sure MongoDB is running locally on port 27017.

```bash
# Windows (if installed as a service, it starts automatically)
# Or run manually:
mongod --dbpath C:\data\db
```

---

### 3. Backend (FastAPI AI Engine)

```bash
# Create and activate virtual environment
python -m venv env
env\Scripts\activate        # Windows
source env/bin/activate     # Mac/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
copy backend\.env.example backend\.env
# Edit backend/.env — set MONGO_URI and TESSERACT_CMD

# Seed websites into the database (run once)
cd backend
python seed_websites.py

# Start the backend
uvicorn main:app --reload --port 8000
```

> **Note:** On first run, AI models (~1.5 GB) are downloaded automatically from HuggingFace. This takes a few minutes. Subsequent starts are instant.

---

### 4. Frontend (React Client)

```bash
cd client

# Install dependencies
npm install

# Configure environment
copy .env.example .env
# Edit client/.env — set VITE_AI_ENGINE_URL=http://localhost:8000

# Start the frontend
npm run dev
# Opens at http://localhost:3000
```

---

### 5. Web_Auth (Demo Password Reset App)

```bash
cd Web_Auth

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit Web_Auth/.env — set MONGO_URI, JWT_SECRET_KEY, FLASK_SECRET_KEY, RESET_API_KEY

# Start Web_Auth
python app.py
# Opens at http://localhost:5000
```

---

## Environment Files

Each service has a `.env.example` — copy it to `.env` and fill in your values:

### `backend/.env`
```env
MONGO_URI=mongodb://localhost:27017/agentic_ai
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### `client/.env`
```env
VITE_AI_ENGINE_URL=http://localhost:8000
```

### `Web_Auth/.env`
```env
MONGO_URI=mongodb://localhost:27017/web_auth
JWT_SECRET_KEY=any-random-secret-string
FLASK_SECRET_KEY=another-random-secret-string
RESET_API_KEY=unisys-reset-secret-key-2024
WEBSITE_NAME=Web_Auth
FLASK_ENV=development
```

> The `RESET_API_KEY` in Web_Auth must match the one stored in the Unisys database by `seed_websites.py`.

---

## Running Order

Start services in this order:

```
1. MongoDB          (always first)
2. Backend          uvicorn main:app --reload --port 8000
3. Web_Auth         python app.py
4. Frontend         npm run dev
```

---

## How It Works

```
Employee submits ticket (React UI)
         ↓
Orchestrator runs the AI pipeline:
  1. Deduplication    — links similar open tickets
  2. NLP Analysis     — classifies category + priority
  3. Risk Assessment  — scores security/business risk
  4. Escalation       — decides auto-resolve vs human review
  5. Remediation      — calls external APIs (e.g. password reset)
  6. Resolution (RAG) — finds best KB match, generates response
  7. Explainability   — confidence scores for each decision
         ↓
Ticket resolved with tailored response shown to employee
```

---

## Features

- **Agentic pipeline** — 7-step multi-agent orchestration
- **Password reset** — AI calls Web_Auth API and returns temp password in ticket
- **Forced password change** — Web_Auth modal forces new password on temp login
- **Linked tickets** — similar issues grouped automatically
- **Risk scoring** — security breaches, compliance violations detected
- **Tailored responses** — each ticket type gets category-specific answer
- **SLA monitoring** — background task tracks ticket SLA breach
- **Multimodal** — upload screenshots/logs for AI analysis
