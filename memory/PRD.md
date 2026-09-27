# Ağıllı Müəllim — PRD

## Original Problem Statement
Parent's child has weak eyesight and cannot read lessons. Build an AI system that scans PDF books, analyzes the topic, explains it simply to the child, does interactive Q&A, and helps solve problems — talking with the child interactively. Azerbaijani language support requested.

## User Choices
- Voice + visual together (TTS read-aloud + large text)
- Ask by typing AND speaking (microphone)
- LLM: Gemini 3.1 Pro (gemini-3.1-pro-preview)
- Level: middle school (11-14)
- No login (single user)
- Languages: Azerbaijani + Turkish

## Architecture
- Backend: FastAPI + MongoDB (motor). LLM via emergentintegrations (Gemini 3.1 Pro, streaming SSE). TTS via OpenAITextToSpeech (tts-1, voice coral). PDFs stored in Emergent Object Storage.
- Frontend: React 19 + Tailwind v4. Accessible, high-contrast, large-font UI (Lexend/Outfit). 3 themes (Parchment/Amber Night/Yellow-Black), font stepper, speed control, AZ/TR toggle.
- Voice input: browser Web Speech API (az-AZ/tr-TR).

## Implemented (2026-06)
- Sample curriculum library (4 seeded books: Biology, Science, Math, History) — auto-seeded on startup
- PDF upload → Gemini analysis (title/subject/summary/topics/child-friendly explanation)
- Interactive streaming chat tutor with per-book context + conversation memory
- 1-click TTS read-aloud on every AI answer with cached audio
- Quick-ask chips (simpler / example / quiz me), mic voice input
- Full accessibility top bar: font size, TTS speed, 3 themes, language toggle
- All tested & passing (backend 4/4 endpoints, frontend all primary flows)

## Backlog
- P1: Interactive quizzes with celebratory audio feedback (TopicSimplifierCard)
- P1: Distraction-free magnifier reading mode with sentence highlighting
- P2: Progress tracking / rewards for the child
- P2: Multiple child profiles
- P2: Per-book delete/rename in library
