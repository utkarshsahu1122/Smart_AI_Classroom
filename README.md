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
- 🎛️ **Custom Weightage** — Faculty can define the exact percentage of MCQs vs Fill-in-the-blanks
- 📱 **QR Code Session** — Auto-generates scannable QR codes for students to join
- 👀 **Live Dashboard** — Real-time student tracking (who joined, who submitted)
- ⛔ **Session Control** — End session anytime; all pending students get auto-submitted
- 📊 **CSV Reports** — Download Excel-compatible CSV reports with scores, statistics, and pass rates

### Student Quiz Module
- 🔐 **Secure Login** — One-time login per roll number; no credential reuse or re-entry after submission
- ⚡ **Instant Quiz** — 10 random questions assigned instantly from the pre-generated pool (zero wait time)
- ⏱️ **Live Timer** — 10-minute countdown with auto-submit on expiry
- 📝 **Dynamic Mix** — Randomizes MCQs and Fill-in-the-blanks based on faculty's set weightage
- 🔄 **Session-End Detection** — Browser automatically submits when faculty ends the session

### Student Doubt Solver (NEW)
- 💬 **ChatGPT-like Interface** — Conversational AI tutor with chat bubbles, typing indicator, and history sidebar
- 📄 **PDF Upload** — Students upload their own study material for context-aware Q&A
- 🧠 **RAG-powered Answers** — Retrieves relevant chunks from the uploaded PDF to answer doubts
- 📝 **Follow-up Support** — Maintains conversation context for multi-turn Q&A
- 📚 **Source Citations** — Expandable source snippets showing which PDF chunks informed the answer
- 📥 **PDF Export** — Download chat summary as a clean, structured PDF document
- ⏰ **7-Day Auto-Expiry** — Chat sessions automatically expire after 7 days with download-before-expiry support

### Security & Authentication
- 🔒 **JWT Authentication** — Token-based auth for the Doubt Solver module
- 🔑 **Bcrypt Passwords** — Secure password hashing with registration + login flow
- 🛡️ **Ownership Enforcement** — Every API checks that students can only access their own data
- 🚫 **Auto-Logout** — Expired tokens trigger automatic re-authentication

### LangGraph Multi-Agent System
- 🤖 **Agent A: Quiz Generator** — LangGraph graph: Load PDF → Build Vectorstore → Retrieve Context → Generate Questions
- 🤖 **Agent B: Doubt Solver** — LangGraph graph: Retrieve Chunks → Generate Conversational Answer
- 🧩 **Extensible Design** — Easy to add new agents (Note Generator, Quiz Evaluator, Feedback Agent)

### AI Intelligence Engine
- 🧠 **RAG Pipeline** — PDF → Text Chunking → FAISS Vector Store → Context Retrieval → Gemini LLM
- 🏠 **Local Embeddings** — Uses HuggingFace `all-MiniLM-L6-v2` (free, fast, runs offline)
- 🎯 **Semantic Questions** — Prompt-engineered to test understanding, not rote memorization
- 📈 **Scalable Pool** — Dynamic question count based on PDF length (3 pages → 30 questions, 25+ pages → 100)
- 🕐 **IST Timezone** — All timestamps displayed in Asia/Kolkata (IST) for Indian users

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
│           ┌──────┴──────┐           │
│           │   MongoDB   │                                    │
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
| **Backend** | Python, Flask, PyMongo, Flask-CORS |
| **AI / RAG** | LangChain, Google Gemini 2.5 Flash, FAISS, HuggingFace Transformers |
| **Database** | MongoDB Atlas (Cloud) |
| **Utilities** | reportlab (PDFs), qrcode (QR generation), PyPDF2 (PDF parsing) |
| **Design** | Custom CSS with glassmorphism dark theme, Inter font |

---

## 📁 Project Structure

```
smart-classroom-ai/
│
├── app/                          # Flask Backend
│   ├── __init__.py               # App factory with CORS
│   ├── models/
│   │   ├── database.py           # PyMongo connection & helpers
│   │   ├── schemas.py            # MongoDB quiz helpers (sessions, students, questions)
│   │   └── chat.py               # MongoDB doubt solver helpers (profiles, chats)
│   ├── routes/
│   │   ├── faculty.py            # Faculty REST API endpoints
│   │   ├── student.py            # Student quiz REST API endpoints
│   │   └── student_doubt.py      # Doubt Solver API (JWT-protected)
│   ├── services/
│   │   ├── langgraph_agents.py   # LangGraph: Agent A (Quiz) + Agent B (Doubt Solver)
│   │   ├── rag_engine.py         # RAG pipeline (delegates to Agent A)
│   │   ├── doubt_solver.py       # Doubt Solver orchestrator
│   │   ├── auth.py               # JWT token generation & auth_required decorator
│   │   ├── pdf_export.py         # PDF export using reportlab
│   │   ├── timezone.py           # UTC → IST timezone conversion
│   │   └── qr_service.py         # QR code generation
│   ├── static/
│   │   ├── temp_uploads/         # Faculty uploaded PDFs & QR codes
│   │   ├── vectorstores/         # FAISS vector indices per quiz session
│   │   ├── doubt_uploads/        # Student uploaded PDFs (doubt solver)
│   │   └── doubt_vectorstores/   # FAISS indices per student document
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
│       │   ├── Navbar.jsx
│       │   ├── ChatBubble.jsx          # Chat message bubble with sources
│       │   └── ChatHistorySidebar.jsx  # Session history sidebar
│       └── pages/
│           ├── FacultyDashboard.jsx
│           ├── SessionDetails.jsx
│           ├── StudentLogin.jsx
│           ├── QuizView.jsx
│           ├── QuizResult.jsx
│           └── StudentDoubtSolver.jsx  # ChatGPT-like doubt solver UI
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

# Configure your Environment Variables
copy .env.template .env
# Edit .env and paste your GOOGLE_API_KEY and MONGO_URI

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

### 6. Run via Docker (Cloud Run Compatible)

Build the image:
```bash
docker build -t smart-classroom-api .
```

Run Docker with env file:
```bash
docker run -p 8080:8080 --env-file .env smart-classroom-api
```

---

## 📖 Usage Guide

### Faculty Workflow
1. Open the **Faculty Dashboard** at `/faculty`
2. **Upload a PDF** of the course material
3. Wait for AI to process and generate the question pool (~15–30s)
4. Share the **QR code** with students (or give them the session code)
5. Monitor the **live student table** to see who's taking the quiz
6. Click **End Session** when time is up — all pending students are auto-submitted
7. **Download the CSV report** with all scores and statistics

### Student Workflow
1. Scan the **QR code** or navigate to the student login
2. Enter **Name**, **Roll Number**, and **Session Code**
3. Receive **10 unique questions** instantly
4. Answer all questions within the **10-minute timer**
5. Submit or get auto-submitted when timer expires / faculty ends session
6. View your **score** immediately

### Doubt Solver Workflow
1. Navigate to **Doubt Solver** tab
2. **Register** with name, roll number, and password (first time) or **Login**
3. **Upload a PDF** of your study material
4. Click **"+ New Chat"** to start a conversation
5. **Ask questions** about the material — AI answers using RAG from your PDF
6. Continue asking follow-up questions in the same chat
7. **Download PDF summary** of your chat anytime
8. Chat sessions auto-expire after **7 days**

---

## 🔌 API Endpoints

### Faculty

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/faculty/upload` | Upload PDF & generate question pool |
| `GET` | `/api/faculty/session/<code>` | Get session details + student list |
| `POST` | `/api/faculty/session/<code>/end` | End session & auto-submit students |
| `GET` | `/api/faculty/session/<code>/report` | Download CSV report |

### Student (Quiz)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/student/login` | Login & get assigned questions |
| `GET` | `/api/student/quiz?student_id=X` | Fetch quiz questions |
| `POST` | `/api/student/submit` | Submit answers & get score |
| `GET` | `/api/student/check_session?session_id=X` | Check if session is active |
| `GET` | `/api/student/result?student_id=X` | Get result details |

### Doubt Solver (JWT Protected)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/doubt/register` | ✗ | Register new student (returns JWT) |
| `POST` | `/api/doubt/login` | ✗ | Login with roll_no + password (returns JWT) |
| `POST` | `/api/doubt/upload-pdf` | ✓ | Upload a PDF for RAG |
| `POST` | `/api/doubt/chat/create` | ✓ | Create new chat session |
| `POST` | `/api/doubt/chat/send` | ✓ | Send question & get AI response |
| `GET` | `/api/doubt/chat/history` | ✓ | List all active chat sessions |
| `GET` | `/api/doubt/chat/<id>/messages` | ✓ | Get messages in a chat |
| `GET` | `/api/doubt/chat/<id>/download` | ✓ | Download chat as PDF |
| `GET` | `/api/doubt/documents` | ✓ | List uploaded PDFs |

---

## 🗺 Future Roadmap

- [ ] **Phase 2** — Speech & Language Module (voice-based interaction)
- [ ] **Phase 3** — Computer Vision Module (attention monitoring)
- [ ] **Model Fine-Tuning** — Custom LLM training on collected quiz data
- [ ] **Faculty Authentication** — Faculty login with JWT
- [ ] **Analytics Dashboard** — Historical performance graphs
- [ ] **New Agents** — Note Generator, Quiz Evaluator, Feedback Agent
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
