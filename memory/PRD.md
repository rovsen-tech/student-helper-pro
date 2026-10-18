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

## Implemented (2026-06 — iteration 2: branding + curriculum)
- Rebranded to "Ağıllı Dərs" everywhere; professional home with hero + subtitle
- Restructured for 5th grade (5-ci sinif). Tutor persona targets 10-11 yaş.
- Azerbaijan 2024-2025 national curriculum: 10 subjects each with its own section and lesson topics (GET /api/subjects)
- Navigation: Home (subjects grid) → SubjectView (lesson list) → TutorChat
- Opening a lesson auto-streams an AI explanation of that topic + TTS
- Session keys: book-{id} / lesson-{md5(subject|topic)} / general; history persisted
- Verified: backend 10/10, frontend all flows

## Implemented (2026-06 — iteration 4: guided learning loop)
- 4-step lesson loop for EVERY lesson (backend stage-aware /api/chat + frontend stage machine):
  1. İzah: system summarizes & teaches the topic simply (auto TTS)
  2. Sən danış: child retells in own words → system praises & gently corrects mistakes
  3. Suallar: system asks voice questions one by one
  4. If child is wrong/"bilmirəm", system re-teaches simpler then re-asks; ends after ~3 Qs
- Stage indicator + big step buttons ("Mövzunu mən danışıram", "Suallara başla")
- Voice answers supported at every step; lesson resets fresh on each open

## Implemented (2026-10 — iteration 5: ChatGPT audit fixes)
- Şagird profilləri (`/api/students`, `X-Student-Id` başlığı, StudentPicker); bütün progress, quiz və chat məlumatları şagirdə görə ayrılır
- İdempotent XP: quiz cavabı üçün unikal indeks, dərs bitirmə üçün atomik claim
- Mənimsəmə modeli XP-dən ayrıdır (ilk cavablar, ≥2 gün, ≥2 quiz)
- LLM suallarının validasiyası (MCQ, arifmetik açar, ipucu sızması), metadata saxlanır
- Xərc limitləri: QUIZ_DAILY_LIMIT, QUIZ_MAX_QUESTIONS, MAX_STUDENTS, QUIZ_LLM_FEEDBACK
- Audit: docs/AUDIT.md, xərc: docs/AI_COST.md

## Backlog
- P1: Interactive quizzes with celebratory audio feedback (TopicSimplifierCard)
- P1: Distraction-free magnifier reading mode with sentence highlighting
- P2: Progress tracking / rewards for the child
- P2: Multiple child profiles
- P2: Per-book delete/rename in library
