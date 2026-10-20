# «Ağıllı Müəllim»: boşluq analizi (Gap Analysis)

**Branch:** `feat/smart-notes` · **Son commit:** `272da10` («Adi kəsrlər» dərs axını düzəlişləri) · **Tarix:** 18.10.2026 · **Mənbə:** repodakı faktiki fayllar (`backend/server.py`, `curriculum.py`, `progress_manager.py`, `quiz_engine.py`, `smart_notes.py`, `frontend/src/**`)

**Status açarları:**

| Status | Mənası |
|---|---|
| ✅ IMPLEMENTED | Kod var və testlə yoxlanılıb |
| 🟡 PARTIAL | Kod var, amma əhatəsi natamamdır |
| ❌ MISSING | Kod yoxdur |
| ⚪ NOT VERIFIED | Kod var, amma real mühitdə/açarla yoxlanılmayıb |

---

### 1. Əsas AI müəllim (Core AI tutor)
| Feature | Status | Notes |
|---|---|---|
| `POST /api/chat` (streaming) | ✅ IMPLEMENTED | Mesaj tarixçəsi `messages`-də saxlanılır, `session_key` şagirdə görə ayrılır |
| Dərs mərhələləri: izah → xatırlama → quiz | ✅ IMPLEMENTED | `TutorChat.jsx`-də `explained` → `recall_input` → `recalled` → `quiz` → `done` keçidləri var |
| Adaptiv sistem mesajı | ✅ IMPLEMENTED | `tutor_system_message(..., mastery)` |
| Mənimsəməyə əsaslanan prompt | ✅ IMPLEMENTED | `/api/chat` `get_mastery()` ilə səviyyəni oxuyur, xəta olarsa `None` ilə davam edir. Mock testlə yoxlanılıb |

### 2. Kurikulum məlumatı və bacarıq xəritəsi
| Feature | Status | Notes |
|---|---|---|
| `curriculum.py` strukturu | ✅ IMPLEMENTED | `learning_outcomes`, `key_concepts`, `common_mistakes`, `sample_problems`, `difficulty_order` |
| Fənn əhatəsi | 🟡 PARTIAL | Riyaziyyatın 7 mövzusunun hamısı, Azərbaycan dilindən 4, Təbiətdən 3 mövzu var. Qalan 7 fənn (İnformatika, İngilis dili, Tarix və s.) kurikulumda yoxdur, onlar üçün prompt kurikulum konteksti olmadan işləyir |
| Prompt-a əlavə edilməsi | ✅ IMPLEMENTED | Təlim nəticələri, anlayışlar və tipik səhvlər sistem mesajına əlavə olunur. Test: `test_system_message` |
| `GET /api/curriculum/{subject}/{topic}` | ✅ IMPLEMENTED | Mövcud mövzu üçün 200, olmayan mövzu üçün 404 (real HTTP) |

### 3. Diaqnostik səhv analizi
| Feature | Status | Notes |
|---|---|---|
| Sessiya daxilində diaqnostik sual | ✅ IMPLEMENTED | Promptda dərsin əvvəlində əvvəlki biliyi yoxlayan bir sual verilməsi tələb olunur. `272da10`: diaqnostik cavaba açıq uyğunlaşma qaydası (səhv → sadə izah + əsas məşq; düz → növbəti mərhələ); tək sadə əməldə düz/səhv deterministik + kurikulum ipucu. Real Gemini ilə yoxlanmayıb |
| «Adi kəsrlər» dərs axını (a–k) | 🟡 PARTIAL | `272da10`: F5-dən sonra tarixçə + mərhələ bərpası (sessionStorage + `/api/messages`), yeni dərs mesajları silmir (`archived`), kontekst ən yeni 20 mesaj, qarışıq ədəd və «ixtisar» yoxlaması, `validate_fraction_answer`. `test_fraction_flow` 13 test (mock + real Mongo). Real Gemini cavab keyfiyyəti və F5 brauzer yoxlaması edilməyib; mini-quiz yalnız «Dərsi bitir»dən sonra əl ilə açılır |
| Şagird üzrə səhv nümunələri: `GET /api/progress/error-analysis` | ✅ IMPLEMENTED | **Yeni.** Səhvlər `question_key` üzrə qruplaşdırılır. Ən çox səhv edilən 10 sual qaytarılır, hər biri üçün kurikulumdan uyğun tipik səhv göstərilir. LLM yoxdur, bazaya yazmır |
| Səhv analizi üçün UI | ✅ IMPLEMENTED | `79dcda5`: `ParentPanel`-də «Ən çox səhv edilən suallar» bölməsi (sual, səhv sayı, ipucu). Brauzerdə real məlumatla yoxlanıb |

### 4. Adaptiv tədris
| Feature | Status | Notes |
|---|---|---|
| Səviyyəyə görə tədris tərzi | ✅ IMPLEMENTED | `level_index` 1-ə qədər və ya məlumat yoxdursa: sadə dil, kiçik addımlar. 2–3: normal temp. 4: daha çətin tapşırıq |
| Real LLM-in bu təlimatlara əməl etməsi | ⚪ NOT VERIFIED | Real Gemini açarı yoxdur |

### 5. Mənimsəməyə əsaslanan təkrar planı
| Feature | Status | Notes |
|---|---|---|
| `GET /api/progress/review-questions` | ✅ IMPLEMENTED | Zəif mövzular və ən çox 5 sual (səhv edilən suallar və kurikulum sualları). Real HTTP-də boş və dolu hallar yoxlanılıb |

### 6. Bacarıq boşluqları endpointi
| Feature | Status | Notes |
|---|---|---|
| `GET /api/progress/skill-gaps` | ✅ IMPLEMENTED | **Yeni.** Hər zəif mövzu üçün düz/səhv sayı, dəqiqlik faizi, mənimsəmə səviyyəsi, kurikulumdan tipik səhvlər və əsas anlayışlar qaytarılır. Ən zəif mövzu birinci gəlir. Bilinməyən şagird üçün 404, boşluq yoxdursa boş siyahı |
| Bacarıq boşluqları üçün UI | ✅ IMPLEMENTED | `79dcda5`: «Bacarıq boşluqları» bölməsi (dəqiqlik %, səhv/düz, tipik səhvlər, əsas anlayışlar). Brauzerdə real məlumatla yoxlanıb |

### 7. Valideyn PIN-i
| Feature | Status | Notes |
|---|---|---|
| Hash + salt saxlanması | ✅ IMPLEMENTED | sha256(salt + pin), `secrets.token_hex(16)`, müqayisə `hmac.compare_digest` ilə |
| `pin-status` / `pin` / `verify` | ✅ IMPLEMENTED | Format səhvdirsə 422; köhnə PIN-siz və ya səhv köhnə PIN ilə dəyişmə 403; hash cavablarda görünmür. Real HTTP: 14/14 keçdi |
| `ParentPinDialog.jsx` qapısı | ✅ IMPLEMENTED | Build keçdi |
| Brute-force məhdudiyyəti | ✅ IMPLEMENTED | `79dcda5`: 5 ardıcıl səhv → 5 dəqiqə HTTP 429 (Azərbaycanca mesaj, `Retry-After`). Düzgün PIN sayğacı sıfırlayır; `/parent/pin` (köhnə PIN) yolu da kilidlənir. Əlavə sahələr: `failed_attempts`, `locked_until`. Dialoq mesajı `role="alert"` ilə göstərir. Testlər: `test_pin_lockout` (mock + real Mongo) |

### 8. Smart Notes (ağıllı qeydlər)
| Feature | Status | Notes |
|---|---|---|
| Ekstraktiv qeydlər, LLM yoxdur | ✅ IMPLEMENTED | `smart_notes.py`. E2E-də LLM çağırışı sayı 0 olaraq yoxlanılıb |
| Bazaya yazmır | ✅ IMPLEMENTED | `/notes/generate` yalnız `messages`-dən oxuyur |

### 9. Quiz mühərriki
| Feature | Status | Notes |
|---|---|---|
| `POST /api/quiz/generate` | ✅ IMPLEMENTED | Validasiya, dublikatların atılması, səhv açarlı sualların atılması; gündəlik limit (11-ci sorğu 429) |
| `POST /api/quiz/submit` | ✅ IMPLEMENTED | Qayda əsaslı yoxlama (məs. «50 faiz» = «50%»), idempotent XP |
| `GET /api/quiz/history` | ✅ IMPLEMENTED | |
| Real LLM ilə quiz yaradılması | ⚪ NOT VERIFIED | Real açar yoxdur, LLM saxtadır |

### 10. İrəliləyişin izlənməsi
| Feature | Status | Notes |
|---|---|---|
| XP, səviyyə, nişanlar, ardıcıl günlər | ✅ IMPLEMENTED | `progress_manager.py`, `/progress/stats` |
| Mənimsəmə (`/progress/mastery`) | ✅ IMPLEMENTED | Hər sualın yalnız ilk cavabı sayılır, XP-dən asılı deyil |

### 11. Çox şagirdli profillər
| Feature | Status | Notes |
|---|---|---|
| `GET` / `POST /api/students`, `X-Student-Id` başlığı | ✅ IMPLEMENTED | Frontend interceptor bütün sorğulara başlığı əlavə edir. E2E-də şagirdlərin məlumatlarının qarışmadığı yoxlanılıb |

### 12. Səsləndirmə (TTS)
| Feature | Status | Notes |
|---|---|---|
| `POST /api/tts` + `useTTS` | 🟡 PARTIAL | Kod var |
| Real Azərbaycan dilində TTS | ⚪ NOT VERIFIED | **NOT RUN:** canlı açar yoxdur |

### 13. Real Gemini yoxlaması
| Feature | Status | Notes |
|---|---|---|
| Real LLM cavab keyfiyyəti | ⚪ NOT VERIFIED | **NOT RUN:** `EMERGENT_LLM_KEY` yoxdur. Bütün testlər saxta LLM ilə aparılıb |

### 14. «Təkrar sualları» UI
| Feature | Status | Notes |
|---|---|---|
| `ReviewQuestions.jsx` + TutorChat düyməsi | ✅ IMPLEMENTED | Brauzerdə real backend ilə yoxlanılıb: səhv cavabı olan şagird üçün 4 sual göstərildi |

### 15. Valideyn paneli
| Feature | Status | Notes |
|---|---|---|
| `/progress/stats` və `/progress/review-questions` | ✅ IMPLEMENTED | `ParentPanel.jsx`, `studentId` dəyişəndə yenidən yüklənir |
| Bacarıq boşluqları və səhv analizi bölmələri | ✅ IMPLEMENTED | `79dcda5`; başlıqlar, `aria-label`, boş vəziyyət, xəta halında `role="alert"` + «Yenidən yüklə» |
| Panelin brauzerdə vizual yoxlanması | ⚪ NOT VERIFIED | Yalnız build yoxlanılıb |

### 16. Əlçatanlıq
| Feature | Status | Notes |
|---|---|---|
| Böyük mətn, kontrast mövzular, şrift ölçüsü | ✅ IMPLEMENTED | `AccessibilityTopBar`, `ReadingMode` (sarı-qara rejim, minimum 36px) |
| `aria-*` atributları və `role="alert"` | 🟡 PARTIAL | `79dcda5`: çatışmayan etiketlər əlavə olundu (geri düymələri, mikrofon + `aria-pressed`, göndər, sual sahəsi, yazı ölçüsü, Valideyn düyməsi, quiz cavab sahəsi). `Home`/`BookLibrary` kartlarında görünən mətn var, ayrıca etiket əlavə edilmədi. Ekran oxuyucu ilə audit edilməyib |
| Klaviatura ilə idarə | 🟡 PARTIAL | `ReadingMode`-da ox düymələri və Esc işləyir, formalar Enter ilə göndərilir. Ekran oxuyucu ilə audit edilməyib |

### 17. Çoxdillilik (i18n)
| Feature | Status | Notes |
|---|---|---|
| `az` + `tr` açarları | ✅ IMPLEMENTED | Hər iki dildə açarlar eynidir (skriptlə yoxlanılıb) |
| Sərt yazılmış mətnlər | 🟡 PARTIAL | `TutorChat.jsx`-də bəzi mətnlər birbaşa Azərbaycan dilində yazılıb («Dərsi bitir», «Mini Quiz», «Suallar hazırlanır...»), i18n-dən keçmir |

### 18. Test əhatəsi
| Feature | Status | Notes |
|---|---|---|
| Mock pytest | ✅ IMPLEMENTED | **112 keçdi** (+13 `test_fraction_flow`), 23 subtest |
| Real MongoDB | ✅ IMPLEMENTED | `test_quiz_progress` 29 + `test_skill_gaps` 4 + `test_pin_lockout` 3 + `test_fraction_flow` 13 = **49 keçdi**. `test_curriculum_pin` (5 test) yalnız mock rejimindədir |
| E2E (real FastAPI + MongoDB, saxta LLM) | ✅ IMPLEMENTED | 39/39 (`agilli_e2e_r4` bazası, bu addımda yenidən işlədildi) |
| Yeni endpointlər, real HTTP | ✅ IMPLEMENTED | 14/14 (əvvəlki addım) |
| Frontend build | ✅ IMPLEMENTED | `vite build` keçir |
| Frontend unit testləri | ❌ MISSING | Jest/Vitest testləri yoxdur |

---

### Növbəti prioritetlər (P2)
1. ~~Bacarıq boşluqları və səhv analizini `ParentPanel`-də göstərmək~~ ✅ `79dcda5`
2. ~~`/parent/verify` üçün cəhd sayını məhdudlaşdırmaq~~ ✅ `79dcda5`
3. Kurikulumu qalan 7 fənnə genişləndirmək.
4. ~~Çatışmayan `aria` etiketləri~~ ✅ `79dcda5`. Qalır: `TutorChat`-dakı sərt yazılmış mətnləri i18n-ə keçirmək, ekran oxuyucu auditi.
5. Real `EMERGENT_LLM_KEY` ilə Gemini və TTS yoxlaması (açar tələb olunur).
