# 🎓 Multimodal Generative AI based Smart Classroom

> An AI-powered Smart Classroom platform that enables faculty to upload course material (PDF) and instantly generate unique, context-aware quizzes for students using **RAG (Retrieval-Augmented Generation)** with **Google Gemini 2.5 Flash**.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Usage Guide](#-usage-guide)
- [API Endpoints](#-api-endpoints)
- [Future Roadmap](#-future-roadmap)
- [Contributors](#-contributors)
- [License](#-license)

---

## ✨ Features

### Faculty Module
- 📄 **PDF Upload** — Upload course material with drag-and-drop
- 🤖 **AI Question Generation** — Automatically generates a pool of 30–100 semantically rich questions using RAG + Gemini 2.5 Flash
- 📱 **QR Code Session** — Auto-generates scannable QR codes for students to join
- 👀 **Live Dashboard** — Real-time student tracking (who joined, who submitted)
- ⛔ **Session Control** — End session anytime; all pending students get auto-submitted
- 📊 **DOCX Reports** — Download professional Word documents with scores, statistics, and pass rates

### Student Module
- 🔐 **Secure Login** — One-time login per roll number; no credential reuse or re-entry after submission
- ⚡ **Instant Quiz** — 10 random questions assigned instantly from the pre-generated pool (zero wait time)
- ⏱️ **Live Timer** — 10-minute countdown with auto-submit on expiry
- 📝 **Mixed Questions** — MCQs with plausible distractors + Fill-in-the-blanks
- 🔄 **Session-End Detection** — Browser automatically submits when faculty ends the session

### AI Intelligence Engine
- 🧠 **RAG Pipeline** — PDF → Text Chunking → FAISS Vector Store → Context Retrieval → Gemini LLM
- 🏠 **Local Embeddings** — Uses HuggingFace `all-MiniLM-L6-v2` (free, fast, runs offline)
- 🎯 **Semantic Questions** — Prompt-engineered to test understanding, not rote memorization
- 📈 **Scalable Pool** — Dynamic question count based on PDF length (3 pages → 30 questions, 25+ pages → 100)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     REACT FRONTEND (Vite)                   │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Faculty  │ │   Session    │ │ Student  │ │   Quiz    │  │
│  │Dashboard │ │   Details    │ │  Login   │ │   View    │  │
│  └────┬─────┘ └──────┬───────┘ └────┬─────┘ └─────┬─────┘  │
│       │               │              │              │        │
│       └───────────────┴──────────────┴──────────────┘        │
│                           │ REST API                         │
├───────────────────────────┼──────────────────────────────────┤
│                     FLASK BACKEND                            │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ Faculty API  │  │ Student API │  │   RAG Engine       │  │
│  │ /api/faculty │  │ /api/student│  │ ┌────────────────┐ │  │
│  └──────┬───────┘  └──────┬──────┘  │ │ PDF → Chunks   │ │  │
│         │                 │         │ │ Chunks → FAISS  │ │  │
│         │                 │         │ │ FAISS → Context │ │  │
│         └────────┬────────┘         │ │ Context → LLM   │ │  │
│                  │                  │ └────────────────┘ │  │
│           ┌──────┴──────┐           └────────────────────┘  │
│           │   SQLite    │                                    │
│           │   Database  │                                    │
│           └─────────────┘                                    │
├──────────────────────────────────────────────────────────────┤
│  EXTERNAL SERVICES                                           │
│  ┌───────────────────┐  ┌─────────────────────────────────┐  │
│  │ HuggingFace       │  │ Google Gemini 2.5 Flash         │  │
│  │ (Local Embeddings)│  │ (Cloud LLM for Q&A Generation)  │  │
│  └───────────────────┘  └─────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, React Router v7 |
| **Backend** | Python, Flask, Flask-SQLAlchemy, Flask-CORS |
| **AI / RAG** | LangChain, Google Gemini 2.5 Flash, FAISS, HuggingFace Transformers |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **Utilities** | python-docx (reports), qrcode (QR generation), PyPDF2 (PDF parsing) |
| **Design** | Custom CSS with glassmorphism dark theme, Inter font |

---

## 📁 Project Structure

```
smart-classroom-ai/
│
├── app/                          # Flask Backend
│   ├── __init__.py               # App factory with CORS
│   ├── models/
│   │   ├── database.py           # SQLAlchemy instance
│   │   └── schemas.py            # DB models (QuizSession, Student, QuizQuestion, StudentQuestion)
│   ├── routes/
│   │   ├── faculty.py            # Faculty REST API endpoints
│   │   └── student.py            # Student REST API endpoints
│   ├── services/
│   │   ├── rag_engine.py         # RAG pipeline (PDF → FAISS → Gemini → Questions)
│   │   └── qr_service.py         # QR code generation
│   ├── static/
│   │   ├── temp_uploads/         # Uploaded PDFs & QR codes
│   │   └── vectorstores/         # FAISS vector indices per session
│   └── templates/                # (Legacy Jinja2 templates, kept for reference)
│
├── frontend/                     # React Frontend (Vite)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js            # Dev proxy → Flask :5000
│   └── src/
│       ├── main.jsx              # Entry point with BrowserRouter
│       ├── App.jsx               # Route definitions
│       ├── index.css             # Premium dark theme design system
│       ├── components/
│       │   └── Navbar.jsx
│       └── pages/
│           ├── FacultyDashboard.jsx
│           ├── SessionDetails.jsx
│           ├── StudentLogin.jsx
│           ├── QuizView.jsx
│           └── QuizResult.jsx
│
├── run.py                        # Flask entry point
├── requirements.txt              # Python dependencies
├── .env.template                 # Environment variable template
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for React frontend)
- **Google Gemini API Key** — Get one free at [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/smart-classroom-ai.git
cd smart-classroom-ai
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
call venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure your API key
copy .env.template .env
# Edit .env and paste your GOOGLE_API_KEY
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the Application

You need **two terminals** running simultaneously:

**Terminal 1 — Flask Backend:**
```bash
call venv\Scripts\activate.bat
python run.py
```
> Backend runs on `http://127.0.0.1:5000`

**Terminal 2 — React Frontend:**
```bash
cd frontend
npm run dev
```
> Frontend runs on `http://127.0.0.1:5173`

### 5. Open the App

Navigate to **http://localhost:5173** in your browser.

---

## 📖 Usage Guide

### Faculty Workflow
1. Open the **Faculty Dashboard** at `/faculty`
2. **Upload a PDF** of the course material
3. Wait for AI to process and generate the question pool (~15–30s)
4. Share the **QR code** with students (or give them the session code)
5. Monitor the **live student table** to see who's taking the quiz
6. Click **End Session** when time is up — all pending students are auto-submitted
7. **Download the DOCX report** with all scores and statistics

### Student Workflow
1. Scan the **QR code** or navigate to the student login
2. Enter **Name**, **Roll Number**, and **Session Code**
3. Receive **10 unique questions** instantly
4. Answer all questions within the **10-minute timer**
5. Submit or get auto-submitted when timer expires / faculty ends session
6. View your **score** immediately

---

## 🔌 API Endpoints

### Faculty

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/faculty/upload` | Upload PDF & generate question pool |
| `GET` | `/api/faculty/session/<code>` | Get session details + student list |
| `POST` | `/api/faculty/session/<code>/end` | End session & auto-submit students |
| `GET` | `/api/faculty/session/<code>/report` | Download DOCX report |

### Student

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/student/login` | Login & get assigned questions |
| `GET` | `/api/student/quiz?student_id=X` | Fetch quiz questions |
| `POST` | `/api/student/submit` | Submit answers & get score |
| `GET` | `/api/student/check_session?session_id=X` | Check if session is active |
| `GET` | `/api/student/result?student_id=X` | Get result details |

---

## 🗺 Future Roadmap

- [ ] **Phase 2** — Speech & Language Module (voice-based interaction)
- [ ] **Phase 3** — Computer Vision Module (attention monitoring)
- [ ] **Model Fine-Tuning** — Custom LLM training on collected quiz data
- [ ] **Authentication** — Faculty login with JWT
- [ ] **Analytics Dashboard** — Historical performance graphs
- [ ] **Deployment** — Docker + cloud hosting

---

## 👥 Contributors

- **Utkarsh Sahu** — Developer & Project Lead

---

## 📄 License

This project is developed as a Final Year Project for academic purposes.

---

<p align="center">
  Built with ❤️ using Flask, React, LangChain & Google Gemini
</p>
