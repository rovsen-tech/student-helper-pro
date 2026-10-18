# Ağıllı Dərs: test hesabatı (PR #1, `feat/smart-notes`)

Tarix: 18.10.2026. PR merge **edilməyib**, Emergent-də deploy **edilməyib**, real verilənlər bazasına heç nə yazılmayıb.

Statuslar: **PASS** (işlədildi və keçdi), **FAIL** (işlədildi və keçmədi), **NOT RUN** (bu mühitdə işlətmək mümkün olmadı).

## 1. Nəticə cədvəli

| # | Yoxlama | Mühit | Saxta (mock) olan hissə | Nəticə |
|---|---------|-------|--------------------------|--------|
| 1 | Frontend tam build | Vite 8, Node | yoxdur | **PASS** (1741 modul; yalnız chunk ölçüsü xəbərdarlığı var) |
| 2 | Backend unit testləri | `requirements.txt` paketləri (real `emergentintegrations==0.2.1`) | Mongo: mongomock | **PASS**: 87 test (quiz 29, notes 22, speech 36) |
| 3 | Backend testləri real Mongo ilə | MongoDB 7.0.14 | LLM | **PASS**: 29/29 |
| 4 | API E2E: real HTTP + real server + real Mongo | uvicorn + MongoDB 7.0 | yalnız LLM və TTS | **PASS**: 39/39 |
| 5 | Brauzer E2E: dərs, quiz, profillər, oxu rejimi | Chrome + build + real backend | LLM və TTS | **PASS** (aşağıda ətraflı) |
| 6 | Real Gemini 3.1 Pro cavabları | — | — | **NOT RUN**: mühitdə `EMERGENT_LLM_KEY` yoxdur |
| 7 | Real OpenAI TTS (Azərbaycan dilində tələffüz) | — | — | **NOT RUN**: açar yoxdur |
| 8 | Emergent preview-in hansı commit-də olduğu | — | — | **NOT RUN**: preview yatmış vəziyyətdədir (`/api/*` 404 qaytarır), panelə çıxış yoxdur |
| 9 | Prod Mongo backup | — | — | **NOT RUN**: DB-yə çıxış yoxdur. Deploy-dan əvvəl siz edin (bax §5) |
| 10 | `tests/test_backend.py` | — | — | **NOT RUN**: canlı preview URL tələb edir |

### API E2E (39 yoxlama, hamısı PASS)
- **Köhnə məlumatlar:** `student_id` olmayan köhnə sənədlər "Əsas profil"ə köçür: 120 XP, "İlk addım" nişanı, dərs, söhbət qorunur.
- **Təhlükəsizlik:** naməlum və ya səhv formatlı profil ID-si (`../../etc`) 404 qaytarır. Cavab açarı şagirdə göndərilmir.
- **İzolyasiya:** söhbət, quiz, statistika, tarixçə və valideyn paneli profillər arasında ayrıdır. B profili A-nın quizinə cavab verməyə çalışanda 404 alır.
- **Sual validasiyası:** səhv açarlı ("2 + 3 = 6") və dublikat suallar atılır.
- **XP:**
  - Səhv cavab 0 XP verir. Eyni suala təkrar cavab da 0 XP verir.
  - **20 paralel** cavabdan XP yalnız 1-nə verilir. **10 paralel** "dərsi bitir" sorğusundan XP yalnız 1-nə verilir.
- **Qısa cavablar:** "0,5" = "1/2", "50 %" və "50 faiz" = "50%". Qərarı qayda verir, LLM çağırılmır.
- **Mənimsəmə:** bir quizdən sonra status "inkişafda" olur. "Mənimsəyib" statusu verilmir.
- **Xərc:** 11-ci quiz 429 qaytarır. Smart Notes 0 LLM çağırışı edir.

### Brauzer E2E (hamısı PASS)
- **Profillər:**
  - "Kim öyrənir?" seçimi işləyir. Yeni profil yaradıldı və "Xoş gəldin" mesajı göründü.
  - Silinmiş profilin ID-si localStorage-da qalanda tətbiq "Əsas profil"ə qayıdır.
- **Dərs axını (Riyaziyyat → Adi kəsrlər):**
  - Mərhələlər ardıcıl keçir: izah → "Mövzunu mən danışıram" → suallar → "Dərsi bitir".
  - "Dərsi bitir" "+50 XP" və "🏅 İlk dərs" mesajını göstərir.
- **Mini Quiz:** səhv cavab qırmızı, düz cavab yaşıl göstərilir. Nəticə ekranı "2 / 4, +40 XP" göstərir, konfetti var.
- **F5-dən sonra:** Test A-da 160 XP, 2 dərs və "Adi kəsrlər: inkişafda" qalır.
- **Profil ayrılığı:** Əsas profil 120 XP, Test B 0 XP göstərir ("Öyrənməyə başla!").
- **Oxu rejimi:** qara fon, sarı iri yazı, cümlə-cümlə göstərilir (1/5 → 2/5). Ox düymələri, "Dinlə/Dayandır" və "Bağla" işləyir.
- **TTS ehtiyat yolu:** backend TTS xətası verəndə (500) brauzer öz səsinə (speechSynthesis) keçir və səs oxunur. Azərbaycan dilində tələffüzün keyfiyyəti VM-də ölçülə bilmədi.
- **Valideyn paneli:** seçilmiş profilin fənn və mövzularını göstərir.

## 2. Tapılan və düzəldilən xətalar

| # | Xəta | Necə tapıldı | Düzəliş |
|---|------|--------------|---------|
| 1 | Test stub-ı real kitabxanaya uyğun deyildi: `StreamDone` 5 məcburi arqument tələb edir və 6 test real paketlərlə uğursuz olurdu | Real `emergentintegrations` ilə pytest | `tests/test_quiz_progress.py` real imzaya uyğunlaşdırıldı |
| 2 | **"3/4 kəsrində surət hansıdır?"** sualı 3÷4 kimi oxunurdu və düzgün sual "səhv açarlı" sayılıb atılırdı | Real HTTP E2E | `quiz_engine.check_arithmetic`: `/` artıq əməl sayılmır, kəsr operand kimi qəbul olunur, yalnız aydın hesablama sualları yoxlanılır |
| 3 | **"50 faiz"** cavabı səhv sayılırdı | Brauzerdə quiz | `parse_number`: "50 faiz", "50 faizi", "%50", "əlli faiz" tanınır |
| 4 | Ekranda xam markdown görünürdü (`**adi kəsrlər**`) | Brauzerdə dərs | `TutorChat.jsx` → `cleanForDisplay`: ekranda `**`, `#`, `` ` `` silinir. TTS-ə gedən mətn dəyişmir |

**Əlavə gücləndirmə:** `ensure_indexes` əvvəllər bir indeks uğursuz olanda qalanlarını atlayırdı. Məsələn, köhnə bazada `quiz_id` təkrarlanırdısa, XP-ni qoruyan unikal indeks yaradılmırdı. İndi hər indeks ayrıca yaradılır, XP indeksi birinci gəlir. İndekslərin adları dəyişməyib.

Hər düzəlişin unit testi var. Testlər real Mongo rejimində də keçir: `TEST_REAL_MONGO_URL=mongodb://localhost:27017 pytest tests/test_quiz_progress.py`.

## 3. Qalan risklər
- **Real Gemini çıxışı yoxlanılmayıb.** Validasiya səhv sualları atır. Etibarlı sual azdırsa 502 qaytarılır və istifadəçi "yenidən cəhd et" görür.
- **Autentifikasiya yoxdur.** Ailə cihazı modelindən istifadə olunur: profil seçilir, şifrə yoxdur.
- **Frontend chunk-ı böyükdür** (893 KB). Tətbiq işləyir, sadəcə ilk yüklənmə bir az yavaş olur.

## 4. Deploy-dan sonra 10 dəqiqəlik yoxlama

| # | Addım | Gözlənilən nəticə |
|---|-------|--------------------|
| 1 | Ana səhifəni açın | Fənlər və "Kim öyrənir?" görünür |
| 2 | "Əsas profil"in XP-sinə baxın | Köhnə XP və nişanlar yerindədir |
| 3 | "+ Yeni profil" ilə "Yoxlama" profili yaradın | Toast çıxır, XP 0-dır |
| 4 | Riyaziyyat → Adi kəsrlər | Müəllim **Azərbaycan dilində** cavab verir, mətndə `**` yoxdur (**real Gemini, ilk dəfə**) |
| 5 | Mesajın səsi | Səs gəlir (**real TTS, ilk dəfə**). Səs gəlmirsə, brauzer səsi işə düşməlidir |
| 6 | "📖 Oxu" | Sarı/qara rejim, oxlar işləyir |
| 7 | Mərhələləri keçin → "Dərsi bitir" | +50 XP |
| 8 | "📝 Mini Quiz": bir sualı səhv, birini düz cavablayın | Səhv: 0 XP, düz: +XP. Suallar 5-ci sinif səviyyəsindədir |
| 9 | F5 basın | XP qalır |
| 10 | "Əsas profil"ə keçin | "Yoxlama" profilinin XP-si orada görünmür |

Xəta olarsa, Emergent backend loglarında `ERROR` sətirlərini kopyalayıb göndərin.

## 5. Deploy və geri qaytarma (rollback)

**Deploy-dan əvvəl:** Mongo bazasının ehtiyat nüsxəsini alın (Emergent panelində və ya `mongodump`).

**Deploy zamanı nə dəyişir:** startup-da `ensure_indexes` köhnə sənədlərə yalnız `student_id="default"` sahəsini **əlavə edir** və indekslər yaradır. Heç bir sənəd və ya kolleksiya **silinmir**.

**Problem olarsa:**
1. Emergent-də əvvəlki versiyaya qayıdın, ya da `main` branch-ı əvvəlki commit-ə qaytarıb yenidən deploy edin.
2. Köhnə kod əlavə olunmuş `student_id` sahəsini nəzərə almır, ona görə məlumat itmir.
3. Yeni yaradılmış profillərin məlumatı bazada qalır. Köhnə kod onları göstərmir, amma silmir də.
4. Son çarə kimi backup-dan bərpa edin.

## 6. Testləri təkrarlamaq

```bash
cd backend
pytest -q tests/ --ignore=tests/test_backend.py          # 87 test
TEST_REAL_MONGO_URL=mongodb://localhost:27017 pytest -q tests/test_quiz_progress.py
cd ../frontend && npx vite build
```
