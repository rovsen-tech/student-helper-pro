"""LLM əsaslı quiz generatoru və cavab qiymətləndiricisi (emergentintegrations / Gemini)."""

import json
import logging
import re
import uuid

logger = logging.getLogger(__name__)

DIFFICULTY_AZ = {"easy": "asan", "medium": "orta", "hard": "çətin"}
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


async def _ask(chat, prompt: str) -> str:
    from emergentintegrations.llm.chat import UserMessage, TextDelta, StreamDone
    buf = ""
    async for ev in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(ev, TextDelta):
            buf += ev.content
        elif isinstance(ev, StreamDone):
            break
    return buf


def _parse_json(text: str):
    m = _JSON_OBJ_RE.search(text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except (ValueError, TypeError):
        return None


def normalize_answer(text) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("İ", "i").lower()).strip(" .!?")


def sanitize_questions(raw, n_questions: int) -> list:
    """LLM cavabını təhlükəsiz, sabit formata salır; yararsız sualları atır."""
    out = []
    for q in (raw or [])[:n_questions]:
        if not isinstance(q, dict):
            continue
        text = str(q.get("question") or "").strip()
        answer = str(q.get("correct_answer") or "").strip()
        if not text or not answer:
            continue
        qtype = q.get("type") if q.get("type") in ("multiple_choice", "short_answer") else "short_answer"
        item = {"id": f"q{len(out) + 1}", "type": qtype, "question": text,
                "correct_answer": answer, "hint": str(q.get("hint") or "").strip()}
        if qtype == "multiple_choice":
            opts = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
            opts = list(dict.fromkeys(opts))[:4]
            if answer not in opts:
                match = next((o for o in opts if normalize_answer(o) == normalize_answer(answer)), None)
                if match:
                    item["correct_answer"] = match
                elif len(opts) == 4:
                    opts[-1] = answer
                else:
                    opts.append(answer)
            if len(opts) < 2:
                item["type"] = "short_answer"
            else:
                item["options"] = opts
        out.append(item)
    return out


def quiz_prompt(topic, subject, difficulty, n_questions) -> str:
    level = DIFFICULTY_AZ.get(difficulty, "asan")
    return (
        f"5-ci sinif şagirdi üçün «{subject}» fənnindən «{topic}» mövzusunda {n_questions} sual hazırla. "
        f"Çətinlik: {level}. Sualların çoxu 4 variantlı (multiple_choice), 1-2-si qısa cavablı (short_answer) olsun. "
        f"Sadə sözlər işlət, şəkilə baxmağı tələb etmə. Hər sual üçün cavabı açıqlamayan qısa ipucu yaz. "
        f"Hamısı Azərbaycan dilində olsun. SADƏCƏ bu formatda düzgün JSON qaytar (başqa mətn yox):\n"
        '{"questions": [{"type": "multiple_choice", "question": "...", "options": ["A","B","C","D"], '
        '"correct_answer": "variantlardan biri, eyni yazılışla", "hint": "..."}, '
        '{"type": "short_answer", "question": "...", "correct_answer": "...", "hint": "..."}]}'
    )


async def generate_quiz(chat_factory, topic, subject, lang="az", difficulty="easy", n_questions=5) -> list:
    n_questions = max(1, min(10, int(n_questions or 5)))
    chat = chat_factory(f"quiz-{uuid.uuid4()}",
                        "Sən 5-ci sinif üçün test sualları hazırlayan müəllimsən. Yalnız JSON qaytar.")
    data = _parse_json(await _ask(chat, quiz_prompt(topic, subject, difficulty, n_questions)))
    return sanitize_questions((data or {}).get("questions"), n_questions)


def quick_evaluate(question: dict, student_answer: str):
    """Variantlı suallar LLM-siz yoxlanır; qısa cavabda dəqiq uyğunluq kifayətdir."""
    if normalize_answer(student_answer) == normalize_answer(question.get("correct_answer")):
        return True
    if question.get("type") == "multiple_choice":
        return False
    return None  # LLM qərar verməlidir


async def evaluate_answer(chat_factory, question: dict, student_answer: str, lang="az") -> dict:
    correct = quick_evaluate(question, student_answer)
    hint = question.get("hint") or ""
    fallback = {
        "correct": bool(correct),
        "score": 10 if correct else 0,
        "feedback": "Düzdür!" if correct else f"Düzgün cavab: {question.get('correct_answer')}. {hint}".strip(),
        "encouragement": "Əla iş, belə davam et! 🎉" if correct else "Narahat olma, növbəti suala birlikdə baxaq! 💪",
    }
    try:
        chat = chat_factory(f"eval-{uuid.uuid4()}",
                            "Sən mehriban 5-ci sinif müəllimisən. Yalnız JSON qaytar.")
        verdict = ("Cavab DÜZDÜR, bunu dəyişmə." if correct is True
                   else "Cavab SƏHVDİR, bunu dəyişmə." if correct is False
                   else "Cavabın mənaca düzgün olub-olmadığını özün qərar ver.")
        prompt = (
            f"Sual: «{question.get('question')}»\nDüzgün cavab: «{question.get('correct_answer')}»\n"
            f"Şagirdin cavabı: «{student_answer}»\n{verdict}\n"
            f"Azərbaycan dilində, 10 yaşlı uşağa uyğun, qısa yaz. Səhvdirsə 'səhvdir' demə, "
            f"mehribanca düzgün cavabı izah et. SADƏCƏ JSON qaytar:\n"
            '{"correct": true, "score": 0-10, "feedback": "1-2 cümlə", "encouragement": "1 qısa cümlə"}'
        )
        data = _parse_json(await _ask(chat, prompt))
    except Exception as e:  # LLM əlçatmazdırsa, sabit cavab qaytarılır
        logger.error(f"Quiz evaluation failed: {e}")
        data = None
    if not isinstance(data, dict):
        return fallback
    is_correct = correct if correct is not None else bool(data.get("correct"))
    try:
        score = max(0, min(10, int(data.get("score", 10 if is_correct else 0))))
    except (TypeError, ValueError):
        score = 10 if is_correct else 0
    return {
        "correct": is_correct,
        "score": score if is_correct else min(score, 5),
        "feedback": str(data.get("feedback") or fallback["feedback"]),
        "encouragement": str(data.get("encouragement") or fallback["encouragement"]),
    }
