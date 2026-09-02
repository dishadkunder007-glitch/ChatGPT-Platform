# ChatGPT Platform 🤖

A production-ready, full-stack AI chat application built with **Next.js 14**, **FastAPI**, and **Groq AI**.

## ✨ Features

- 🎯 **Complete ChatGPT-style UI** — Dark theme, sidebar, streaming responses
- 🔐 **Authentication** — Register, login, Google OAuth, password reset, session management
- 💬 **Chat Features** — New chat, rename, delete, search, multi-turn conversations
- ⚡ **Real-time Streaming** — Token-by-token AI responses via SSE
- 🔄 **Message Controls** — Copy, edit, regenerate, thumbs up/down feedback
- 📝 **Markdown Rendering** — Tables, code blocks with syntax highlighting, lists
- 📁 **File Upload** — PDF, DOCX, TXT, CSV, JSON — drag & drop
- 🔍 **RAG Q&A** — Document-grounded answers with source citations
- 👤 **User Profile** — Avatar, settings, API key, system prompt, account deletion
- 📱 **Responsive** — Full desktop & mobile support

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10+ 
- Node.js 18+
- A free [Groq API key](https://console.groq.com) (100k tokens/day free)

### 1. Backend Setup

```bash
cd ChatGPT-Platform/backend

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# Start backend (port 8000)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd ChatGPT-Platform/nextjs-frontend

# Install dependencies
npm install

# Copy environment file
copy .env.local.example .env.local

# Start frontend (port 3000)
npm run dev
```

### 3. Open the App

Navigate to **[http://localhost:3000](http://localhost:3000)** 🎉

---

## 🌩️ Cloud Deployment

### Option A: Vercel (Frontend) + Render (Backend)

#### Deploy Backend to Render

1. Create a [Render](https://render.com) account (free)
2. New → Web Service → Connect your GitHub repo
3. Settings:
   - **Root Directory**: `ChatGPT-Platform/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Environment Variables:
   - `GROQ_API_KEY` = your key
   - `DATABASE_URL` = (add a free PostgreSQL add-on from Render)
   - `JWT_SECRET_KEY` = a strong random string
   - `FRONTEND_URL` = your Vercel URL

#### Deploy Frontend to Vercel

1. Create a [Vercel](https://vercel.com) account (free)
2. Import project → Select your GitHub repo
3. Settings:
   - **Root Directory**: `ChatGPT-Platform/nextjs-frontend`
   - **Framework Preset**: Next.js
4. Environment Variables:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` = (optional, for Google OAuth)
5. Deploy! 🚀

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Free at console.groq.com |
| `DATABASE_URL` | ✅ | SQLite (local) or PostgreSQL (cloud) |
| `JWT_SECRET_KEY` | ✅ | Random secret for JWT signing |
| `FRONTEND_URL` | ✅ | For password reset links |
| `GOOGLE_CLIENT_ID` | Optional | For Google OAuth |
| `SMTP_USER` / `SMTP_PASSWORD` | Optional | For password reset emails (Gmail) |

### Frontend (`nextjs-frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend URL (e.g., http://localhost:8000) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID |

---

## 🔑 Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable **Google Identity Platform** API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized origins:
   - `http://localhost:3000` (development)
   - Your Vercel URL (production)
6. Copy the **Client ID** to `NEXT_PUBLIC_GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_ID`

---

## 📧 Gmail Password Reset Setup

1. Enable 2-Factor Authentication on your Gmail account
2. Go to Google Account → Security → App Passwords
3. Create an App Password for "Mail"
4. Use the generated 16-character password as `SMTP_PASSWORD`
5. Set `SMTP_USER` and `EMAIL_FROM` to your Gmail address

> 💡 **Development**: If email is not configured, reset links print to the backend console.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| State | Zustand |
| Markdown | react-markdown + react-syntax-highlighter |
| Backend | FastAPI, Python 3.10+ |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy |
| Auth | JWT + bcrypt + Google OAuth |
| AI | Groq Cloud (Llama 3.3 70B, Mixtral, Qwen Coder) |
| RAG | In-memory FAISS-like vector store |
| Deployment | Vercel + Render |

---

## 📁 Project Structure

```
ChatGPT-Platform/
├── backend/
│   ├── main.py              # All API endpoints
│   ├── database.py          # SQLAlchemy models
│   ├── auth.py              # JWT + Google OAuth
│   ├── models.py            # Pydantic schemas
│   ├── groq_client.py       # AI streaming
│   ├── document_processor.py # PDF/DOCX parsing
│   ├── rag.py               # RAG retrieval
│   ├── email_service.py     # Gmail SMTP
│   └── requirements.txt
│
└── nextjs-frontend/
    ├── app/
    │   ├── page.tsx          # Main chat page
    │   ├── layout.tsx        # Root layout
    │   ├── providers.tsx     # Auth initialization
    │   └── reset-password/   # Password reset page
    ├── components/
    │   ├── layout/           # Sidebar, Header
    │   ├── chat/             # ChatArea, MessageBubble, InputBox
    │   └── modals/           # Auth, Settings, Documents, Profile
    ├── lib/
    │   ├── api.ts            # All API calls + SSE streaming
    │   ├── store.ts          # Zustand global state
    │   └── utils.ts          # Helper functions
    └── types/index.ts        # TypeScript interfaces
```
