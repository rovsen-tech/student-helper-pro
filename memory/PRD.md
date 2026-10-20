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

## Implemented (2026-06 — iteration 5: error-loop fix + Tutor Core + voices)
- FIXED critical TTS error-loop: backend emits SSE {error:true} on failure (no apology text, not persisted); frontend shows a silent error + manual "Yenidən cəhd et" retry button and never auto-speaks errors; no infinite retry
- Upgraded Tutor Core system prompt per pedagogy spec (rules 42-62): chunk→check→continue, active understanding checks instead of "başa düşdün?", think-time, minimum help, error-as-information, no fake praise, adaptive difficulty
- Speech-prep layer: verbalizes fractions/percent/×/÷/=/° for natural Azerbaijani TTS
- Two teacher voices (Mülayim=coral / Canlı=nova), persisted to localStorage
- TTS token guard prevents overlapping/duplicate audio (prior fix retained)

## Deferred (pedagogy spec, needs dedicated phase)
- Stateful student model, mastery tracking, spaced review, cross-session memory (rules 56,59-61,66-68)
- Interactive chunked voice loop with interrupt controls (Dayandır/Daha sadə/Başqa cür izah et) beyond current quick-asks (rule 51)
- Accessible visual teaching tools: number lines, fraction bars, high-contrast diagrams (rules 65,69)

## Backlog
- P1: Interactive quizzes with celebratory audio feedback (TopicSimplifierCard)
- P1: Distraction-free magnifier reading mode with sentence highlighting
- P2: Progress tracking / rewards for the child
- P2: Multiple child profiles
- P2: Per-book delete/rename in library

## 2026-06 — origin/main merge (branch feature/merge-main)
- Merged origin/main (AZ teacher prompt, greeting+diagnostic start, session summary, hold-to-record mic, no startup deletion, speech_preparation.py, Smart Notes, quiz/progress, StudentPicker, parent PIN, curriculum).
- Kept: textbook lesson_source grounding, voice choice (coral/nova), lesson resume, manual retry.
- Student identity unified on main's X-Student-Id header (old body student_id removed).
- Fixed: retry duplicate bubbles (frontend), duplicate user message on retry (backend).
- DB preserved: 39 lessons / 79 blocks. Backup JSON in /app/backup. pytest 120 passed; iteration_6 frontend passed.
## Open
- Recall button visible before diagnostic answered; Riyaziyyat card says "7 mövzu" vs 39 lessons; PDF text quality unverified.
