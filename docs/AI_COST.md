# AI xərci: hansı funksiya AI işlədir?

## AI işlədənlər (ödənişli, `EMERGENT_LLM_KEY`)

| Funksiya | Model | Nəzarət |
|----------|-------|---------|
| Müəllim çatı (`/api/chat`) | Gemini | Hər mesajda bir çağırış |
| PDF dərslik analizi (yükləmə) | Gemini | Yalnız yükləmə zamanı |
| Səsləndirmə (TTS) | OpenAI TTS | Keşlənir, eyni mətn yenidən ödənilmir |
| Quiz yaratma (`/api/quiz/generate`) | Gemini | `QUIZ_DAILY_LIMIT` (gündə, hər şagird üçün), `QUIZ_MAX_QUESTIONS` |
| Qısa cavabın semantik yoxlanması | Gemini | Yalnız deterministik qərar mümkün olmayanda |

## AI işlətməyənlər (pulsuz)

- Smart Notes (ekstraktivdir, DB-yə yazmır)
- MCQ, ədədi və normallaşdırılmış mətn cavablarının yoxlanması
- XP, mənimsəmə və statistika

## Mühit dəyişənləri

| Dəyişən | Default | Mənası |
|---------|---------|--------|
| `QUIZ_DAILY_LIMIT` | 10 | Bir şagirdin gündə yarada biləcəyi quiz sayı (limit aşılanda 429) |
| `QUIZ_MAX_QUESTIONS` | 5 | Bir quizdəki maksimum sual sayı |
| `MAX_STUDENTS` | 10 | Maksimum profil sayı |
| `QUIZ_LLM_FEEDBACK` | 0 | `1` olarsa, deterministik yoxlanan cavablara da LLM rəyi alınır (xərci artırır) |
