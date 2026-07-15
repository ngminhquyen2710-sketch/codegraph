# CodeExplorer AI

A simple web interface that loads a GitHub repository, builds a code graph, and lets you ask questions about the code using an AI chat assistant.

## What it does

- Load a public GitHub repository URL
- Parse repository files into an interactive graph
- Provide a chat interface for code-aware questions
- Use embeddings and retrieval for better answers

## Tech stack

- Backend: FastAPI (Python)
- Frontend: React + Vite
- Styling: TailwindCSS
- Graph logic: custom repository parser and graph retrieval

## Run locally

1. Backend:
   ```powershell
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   # edit .env if you want to use a real OpenAI key
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

3. Open your browser at `http://localhost:3000`

## Notes

- Use a GitHub repo URL to generate the graph.
- If you want AI answers, configure the OpenAI key in `backend/.env`.
