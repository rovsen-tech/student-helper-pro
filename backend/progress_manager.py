"""XP, səviyyə, nişan, ardıcıl günlər və mənimsəmə (mastery) — MongoDB üzərində.

Bütün məlumatlar `student_id` ilə ayrılır. XP motivasiya üçündür; biliyin
ölçüsü ayrıca `compute_mastery` ilə hesablanır.
"""

import hashlib
import re
from datetime import date, datetime, timedelta, timezone

DEFAULT_STUDENT = "default"
LEGACY_PROFILE_ID = "student"  # köhnə tək-profil sənədi "default" şagirdə aiddir

XP_LESSON = 50
XP_QUIZ_CORRECT = 20
XP_PERFECT_QUIZ = 100

LEVELS = [(0, "Yeni başlayan"), (200, "Öyrənən"), (500, "Çalışqan"), (1000, "Ustalaşan"), (2000, "Deha")]

BADGE_FIRST_LESSON = "İlk dərs"
BADGE_PERFECT_QUIZ = "Quiz qalibi"
BADGE_STREAK_5 = "5 dərs ardıcıl"
BADGE_SUBJECT_MASTER = "Fənn ustası"

MASTERY_NONE = "başlanmayıb"
MASTERY_LEVELS = ["başlanğıc", "inkişafda", "mənimsəyir", "mənimsəyib"]
RECENT_WINDOW = 10


def profile_id(student_id: str) -> str:
    return LEGACY_PROFILE_ID if student_id == DEFAULT_STUDENT else f"student:{student_id}"


def level_info(xp: int) -> dict:
    xp = max(0, int(xp or 0))
    idx = max(i for i, (lo, _) in enumerate(LEVELS) if xp >= lo)
    lo, name = LEVELS[idx]
    hi = LEVELS[idx + 1][0] if idx + 1 < len(LEVELS) else None
    pct = 100 if hi is None else round((xp - lo) * 100 / (hi - lo))
    return {"level": name, "level_index": idx + 1, "level_min": lo, "level_max": hi, "level_progress_pct": pct}


def compute_streak(days, today: date) -> int:
    """Bu gün (və ya dünən) bitən ardıcıl günlərin sayı."""
    ds = {date.fromisoformat(d) for d in days or []}
    cur = today if today in ds else today - timedelta(days=1)
    n = 0
    while cur in ds:
        n += 1
        cur -= timedelta(days=1)
    return n


def question_key(text: str) -> str:
    norm = re.sub(r"\s+", " ", str(text or "").lower()).strip()
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


def compute_mastery(answers: list) -> dict:
    """Mənimsəmə səviyyəsi — XP-dən asılı deyil.

    `answers`: [{correct, question_key, quiz_id, day, question}] (köhnədən yeniyə).
    Yalnız hər sualın İLK cavabı nəzərə alınır (təkrar cəhdlə şişirtmək olmaz).
    """
    seen, firsts = set(), []
    for a in answers or []:
        k = a.get("question_key")
        if k in seen:
            continue
        seen.add(k)
        firsts.append(a)
    if not firsts:
        return {"level": MASTERY_NONE, "level_index": 0, "answered": 0, "distinct_correct": 0,
                "recent_accuracy_pct": 0, "quizzes": 0, "days": 0, "review_questions": []}
    recent = firsts[-RECENT_WINDOW:]
    acc = sum(1 for a in recent if a.get("correct")) / len(recent)
    distinct_correct = sum(1 for a in firsts if a.get("correct"))
    quizzes = len({a.get("quiz_id") for a in firsts})
    days = len({a.get("day") for a in firsts})
    if distinct_correct >= 8 and acc >= 0.8 and quizzes >= 2 and days >= 2:
        idx = 4
    elif distinct_correct >= 4 and acc >= 0.6:
        idx = 3
    elif acc >= 0.3 or distinct_correct >= 2:
        idx = 2
    else:
        idx = 1
    review = [a.get("question") for a in reversed(recent) if not a.get("correct") and a.get("question")][:3]
    return {"level": MASTERY_LEVELS[idx - 1], "level_index": idx, "answered": len(firsts),
            "distinct_correct": distinct_correct, "recent_accuracy_pct": round(acc * 100),
            "quizzes": quizzes, "days": days, "review_questions": review}


def _now():
    return datetime.now(timezone.utc)


async def ensure_indexes(db) -> None:
    """İdempotent, dağıdıcı olmayan indekslər + köhnə sənədlərə student_id əlavəsi."""
    for coll in ("progress", "activity_log", "quizzes"):
        await db[coll].update_many({"student_id": {"$exists": False}}, {"$set": {"student_id": DEFAULT_STUDENT}})
    specs = [
        ("quiz_answers", [("student_id", 1), ("quiz_id", 1), ("question_id", 1)], True),  # XP idempotentliyi
        ("progress", [("student_id", 1), ("subject", 1), ("topic", 1)], False),
        ("activity_log", [("student_id", 1), ("created_at", -1)], False),
        ("quizzes", [("quiz_id", 1)], True),
        ("quizzes", [("student_id", 1), ("created_at", -1)], False),
        ("quiz_answers", [("student_id", 1), ("subject", 1), ("topic", 1), ("created_at", 1)], False),
        ("students", [("id", 1)], True),
        ("messages", [("session_id", 1), ("created_at", 1)], False),
    ]
    failed = []
    for coll, keys, unique in specs:
        try:  # bir indeksin uğursuzluğu digərlərini (xüsusən XP unikal indeksini) atlamasın
            await db[coll].create_index(keys, unique=unique)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{coll}{keys}: {e}")
    if failed:
        raise RuntimeError("Index setup partially failed: " + "; ".join(failed))


async def _profile(db, sid) -> dict:
    return await db.student_profile.find_one({"_id": profile_id(sid)}) or {}


async def add_xp(db, sid, amount: int, reason: str, subject=None, topic=None) -> int:
    doc = await db.student_profile.find_one_and_update(
        {"_id": profile_id(sid)},
        {"$inc": {"total_xp": amount}, "$setOnInsert": {"badges": [], "lesson_days": [], "student_id": sid}},
        upsert=True, return_document=True)
    await db.activity_log.insert_one({"student_id": sid, "type": reason, "xp": amount, "subject": subject,
                                      "topic": topic, "created_at": _now().isoformat()})
    return int((doc or {}).get("total_xp", amount))


async def award_badge(db, sid, badge: str) -> bool:
    res = await db.student_profile.update_one(
        {"_id": profile_id(sid), "badges": {"$ne": badge}}, {"$push": {"badges": badge}}, upsert=False)
    if res.modified_count:
        await db.activity_log.insert_one({"student_id": sid, "type": "badge", "badge": badge, "xp": 0,
                                          "created_at": _now().isoformat()})
        return True
    return False


async def record_lesson_complete(db, sid, subject: str, topic: str, subject_topics=None) -> dict:
    """XP yalnız İLK tamamlamada verilir (atomik); təkrar tamamlama qeyd olunur, XP 0."""
    now = _now()
    today = now.date()
    key = {"student_id": sid, "subject": subject, "topic": topic}
    await db.progress.update_one(key, {"$setOnInsert": {"started_at": now.isoformat()}}, upsert=True)
    claim = await db.progress.update_one(
        {**key, "lesson_completed": {"$ne": True}},
        {"$set": {"lesson_completed": True, "completed_at": now.isoformat()}})
    first_time = bool(claim.modified_count)
    await db.progress.update_one(key, {"$inc": {"lesson_complete_count": 1},
                                       "$set": {"last_active": now.isoformat()}})
    xp = XP_LESSON if first_time else 0
    total = await add_xp(db, sid, xp, "lesson_complete" if first_time else "lesson_repeat", subject, topic)
    await db.student_profile.update_one({"_id": profile_id(sid)}, {"$addToSet": {"lesson_days": today.isoformat()}})

    profile = await _profile(db, sid)
    earned = []
    if await award_badge(db, sid, BADGE_FIRST_LESSON):
        earned.append(BADGE_FIRST_LESSON)
    if compute_streak(profile.get("lesson_days"), today) >= 5 and await award_badge(db, sid, BADGE_STREAK_5):
        earned.append(BADGE_STREAK_5)
    if subject_topics:
        done = await db.progress.count_documents(
            {"student_id": sid, "subject": subject, "topic": {"$in": list(subject_topics)}, "lesson_completed": True})
        if done >= len(subject_topics) and await award_badge(db, sid, BADGE_SUBJECT_MASTER):
            earned.append(BADGE_SUBJECT_MASTER)
    info = level_info(total)
    return {"xp_earned": xp, "new_total_xp": total, "level": info["level"], "first_time": first_time,
            "badge_earned": earned[0] if earned else None, "badges_earned": earned,
            "confetti": bool(earned) or first_time}


async def record_quiz_answer(db, sid, quiz_id, question: dict, subject, topic, correct: bool) -> int:
    """Cavabı quiz_answers-ə yazır (unikal indeks təkrarı bloklayır) və XP verir."""
    now = _now()
    try:
        await db.quiz_answers.insert_one({
            "student_id": sid, "quiz_id": quiz_id, "question_id": question["id"],
            "question_key": question_key(question.get("question")), "question": question.get("question"),
            "subject": subject, "topic": topic, "correct": bool(correct),
            "day": now.date().isoformat(), "created_at": now.isoformat()})
    except Exception as exc:  # DuplicateKeyError — paralel təkrar sorğu
        if "duplicate" in str(exc).lower() or exc.__class__.__name__ == "DuplicateKeyError":
            return 0
        raise
    inc = {"quiz_attempts": 1, "quiz_correct": 1 if correct else 0}
    xp = XP_QUIZ_CORRECT if correct else 0
    await db.progress.update_one(
        {"student_id": sid, "subject": subject, "topic": topic},
        {"$inc": inc, "$set": {"last_quiz_at": now.isoformat(), "last_active": now.isoformat()},
         "$setOnInsert": {"started_at": now.isoformat()}},
        upsert=True)
    if xp:
        await add_xp(db, sid, xp, "quiz_correct", subject, topic)
    return xp


async def record_perfect_quiz(db, sid, subject, topic) -> dict:
    await add_xp(db, sid, XP_PERFECT_QUIZ, "perfect_quiz", subject, topic)
    badge = BADGE_PERFECT_QUIZ if await award_badge(db, sid, BADGE_PERFECT_QUIZ) else None
    return {"xp": XP_PERFECT_QUIZ, "badge": badge}


async def get_mastery(db, sid, subject=None, topic=None) -> list:
    query = {"student_id": sid}
    if subject:
        query["subject"] = subject
    if topic:
        query["topic"] = topic
    docs = await db.quiz_answers.find(query, {"_id": 0}).sort("created_at", 1).to_list(5000)
    groups = {}
    for d in docs:
        groups.setdefault((d["subject"], d["topic"]), []).append(d)
    return [{"subject": s, "topic": t, **compute_mastery(a)} for (s, t), a in groups.items()]


async def get_student_stats(db, sid) -> dict:
    profile = await _profile(db, sid)
    total_xp = int(profile.get("total_xp", 0))
    docs = await db.progress.find({"student_id": sid}).to_list(2000)
    attempts = sum(d.get("quiz_attempts", 0) for d in docs)
    correct = sum(d.get("quiz_correct", 0) for d in docs)
    recent = await db.activity_log.find({"student_id": sid}, {"_id": 0}).sort("created_at", -1).to_list(10)
    mastery = await get_mastery(db, sid)
    summary = {lvl: 0 for lvl in MASTERY_LEVELS}
    for m in mastery:
        summary[m["level"]] = summary.get(m["level"], 0) + 1
    return {
        "student_id": sid,
        "total_xp": total_xp,
        **level_info(total_xp),
        "streak_days": compute_streak(profile.get("lesson_days"), _now().date()),
        "lessons_complete": sum(1 for d in docs if d.get("lesson_completed")),
        "quiz_attempts": attempts,
        "quiz_correct_pct": round(correct * 100 / attempts) if attempts else 0,
        "badges": profile.get("badges", []),
        "recent_activity": recent,
        "mastery_summary": summary,
        "topics_mastered": summary.get("mənimsəyib", 0),
        "mastery": mastery,
    }
