# Ağıllı Dərs: PR #1 auditi (A/B/C)

Bu audit ChatGPT-nin PR #1 üzrə rəyinə əsaslanır. Hər bəndin statusu:
**TƏSDİQLƏNİB** (testlə və ya kodla yoxlanılıb), **TƏSDİQLƏNMƏYİB** (yoxlanılmayıb və ya problem qalır), **BİLMİRƏM** (bu mühitdə yoxlamaq mümkün deyil).

## A. Düzgün işləyənlər

| # | Bənd | Status | Harada |
|---|------|--------|--------|
| A1 | Smart Notes ekstraktivdir: LLM çağırmır, DB-yə yazmır | TƏSDİQLƏNİB (19 test keçir, 1-i ötürülür) | `backend/smart_notes.py` |
| A2 | MCQ və ədədi cavablar LLM-siz, deterministik yoxlanır | TƏSDİQLƏNİB | `quiz_engine.quick_evaluate`, `answers_equal` |
| A3 | TTS keşlənir, eyni mətn üçün təkrar ödəniş olmur | TƏSDİQLƏNMƏYİB (kodda var, bu turda test edilməyib) | `server.py` TTS endpoint |

> Qeyd: əvvəlki PR mətnində "20 Smart Notes testi ✅" yazılmışdı. Əslində 19 test keçir, 1-i ötürülür (skipped).

## B. Risklər və bu commit-də nə düzəldi

| # | Risk (ChatGPT) | Düzəliş | Status |
|---|----------------|---------|--------|
| B1 | Şagird izolyasiyası yox idi (`PROFILE_ID="student"` sabiti) | `X-Student-Id` başlığı, `current_student` dependency; bütün progress/quiz/chat sorğuları `student_id` ilə filtrlənir; başqasının quizinə `submit` 404 qaytarır | TƏSDİQLƏNİB (mock Mongo testləri) |
| B2 | Paralel və ya təkrar sorğuda XP iki dəfə verilir | `quiz_answers` üzrə unikal indeks (student_id, quiz_id, question_id); dərs bitirmə `lesson_completed $ne True` ilə atomik claim olunur | TƏSDİQLƏNİB (`asyncio.gather` testi və real MongoDB 7.0-da 20 paralel HTTP sorğusu: XP yalnız bir dəfə verilir) |
| B3 | XP ilə mənimsəmə qarışıqdır | `compute_mastery`: hər sualın yalnız ilk cavabı, son 10 cavab; "mənimsəyib" üçün ≥8 fərqli düz cavab, ≥80%, ≥2 quiz, ≥2 gün | TƏSDİQLƏNİB (`MasteryTests`) |
| B4 | Qısa cavab yoxlaması zəifdir | Azərbaycan hərfləri (İ/ı), durğu işarələri, 0,5 = 1/2 = yarım = 50%, ədəd sözləri, rəqəmdən sonra gələn vahidlər | TƏSDİQLƏNİB (unit testlər) |
| B5 | LLM-in yaratdığı sual və açar yoxlanmır | `validate_questions`: MCQ-də tam 4 fərqli variant olmalı, açar dəqiq birinə uyğun gəlməlidir. Səhv arifmetik açarlı, dublikat və boş suallar atılır. Cavabı açan ipucu silinir. Metadata saxlanır (model, validation_version, dropped_questions). Etibarlı sual azdırsa 502 qaytarılır | TƏSDİQLƏNİB (mock). Real Gemini çıxışında BİLMİRƏM |
| B6 | AI xərci nəzarətsizdir | Gündəlik quiz limiti (429), quiz başına sual limiti, profil limiti; deterministik qərar mümkündürsə LLM-lə qiymətləndirmə edilmir. Bax: `docs/AI_COST.md` | TƏSDİQLƏNİB (429 testi) |
| B7 | İndekslər dağıdıcı ola bilər | `ensure_indexes`: köhnə sənədlərə `student_id="default"` yazılır, sonra indekslər yaradılır, heç nə silinmir | TƏSDİQLƏNİB (mock backfill testi) |

### Qalan risklər (düzəlməyib)

- **Autentifikasiya yoxdur.** Ailə cihazı modeli tətbiq olunur: profil seçilir, amma şifrə yoxdur. Profil ID-si təxmin edilməsi çətin olan uuid hex-dir, lakin bu, autentifikasiya sayılmaz. Status: TƏSDİQLƏNMƏYİB (açıq risk).
- **Kurrikuluma uyğunluq yalnız prompt-a əsaslanır.** Status: BİLMİRƏM.
- **`tests/test_backend.py`** canlı server və pytest tələb edir. Bu mühitdə işləmir və bu vəziyyət dəyişikliklərdən əvvəl də belə idi.
- Smart Notes-un keyfiyyəti real dərsliklərdə ölçülməyib. Status: BİLMİRƏM.

## C. Prioritetli plan

1. Riyaziyyatdan bir tam dərs axınını real Gemini və real MongoDB ilə (Emergent preview) sınamaq.
2. ~~Brauzer testi: profil seçimi, quiz, mənimsəmə chip-ləri, 429 mesajı.~~ Lokal mühitdə edildi (bax: `docs/TEST_REPORT.md`).
3. Valideyn üçün sadə PIN (profil yaratma və silmə əməliyyatları üçün).
4. Mənimsəmə əsasında "təkrar suallar" (`review_questions`) ekranı.

## Test matrisi

| Sahə | Mock / unit | Real |
|------|-------------|------|
| Quiz validasiyası, normallaşdırma, mastery | ✅ 29 test keçir (`test_quiz_progress.py`) | n/a |
| İzolyasiya, idempotent XP, limitlər | ✅ mongomock-motor | ✅ real MongoDB 7.0 (29 test + 39 HTTP yoxlaması) |
| Smart Notes | ✅ 22 keçir (real paketlərlə) | n/a (LLM yoxdur) |
| Speech preparation | ✅ 36 keçir | n/a |
| Gemini və OpenAI TTS | ⚠️ saxta | ❌ yoxlanılmayıb (açar yoxdur) |
| Frontend | ✅ tam Vite build | ✅ brauzer E2E (saxta LLM ilə) |
| Emergent deploy | ❌ | ❌ |

Ətraflı nəticələr: `docs/TEST_REPORT.md`.
