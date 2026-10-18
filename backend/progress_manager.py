"""XP, səviyyə, nişan və ardıcıl günlər (streak) — MongoDB üzərində."""

from datetime import date, datetime, timedelta, timezone

XP_LESSON = 50
XP_QUIZ_CORRECT = 20
XP_PERFECT_QUIZ = 100

LEVELS = [(0, "Yeni başlayan"), (200, "Öyrənən"), (500, "Çalışqan"), (1000, "Ustalaşan"), (2000, "Deha")]

BADGE_FIRST_LESSON = "İlk dərs"
BADGE_PERFECT_QUIZ = "Quiz qalibi"
BADGE_STREAK_5 = "5 dərs ardıcıl"
BADGE_SUBJECT_MASTER = "Fənn ustası"

PROFILE_ID = "student"


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


def _now():
    return datetime.now(timezone.utc)


async def _profile(db) -> dict:
    return await db.student_profile.find_one({"_id": PROFILE_ID}) or {}


async def add_xp(db, amount: int, reason: str, subject=None, topic=None) -> int:
    now = _now().isoformat()
    doc = await db.student_profile.find_one_and_update(
        {"_id": PROFILE_ID}, {"$inc": {"total_xp": amount}, "$setOnInsert": {"badges": [], "lesson_days": []}},
        upsert=True, return_document=True)
    await db.activity_log.insert_one({"type": reason, "xp": amount, "subject": subject,
                                      "topic": topic, "created_at": now})
    return int((doc or {}).get("total_xp", amount))


async def award_badge(db, badge: str) -> bool:
    res = await db.student_profile.update_one(
        {"_id": PROFILE_ID, "badges": {"$ne": badge}}, {"$push": {"badges": badge}}, upsert=False)
    if res.modified_count:
        await db.activity_log.insert_one({"type": "badge", "badge": badge, "xp": 0,
                                          "created_at": _now().isoformat()})
        return True
    return False


async def record_lesson_complete(db, subject: str, topic: str, subject_topics=None) -> dict:
    now = _now()
    today = now.date()
    prev = await db.progress.find_one({"subject": subject, "topic": topic}) or {}
    first_time = not prev.get("lesson_completed")
    await db.progress.update_one(
        {"subject": subject, "topic": topic},
        {"$set": {"lesson_completed": True, "completed_at": now.isoformat(), "last_active": now.isoformat()},
         "$inc": {"lesson_complete_count": 1}, "$setOnInsert": {"started_at": now.isoformat()}},
        upsert=True)
    xp = XP_LESSON if first_time else XP_LESSON // 5
    total = await add_xp(db, xp, "lesson_complete", subject, topic)
    await db.student_profile.update_one({"_id": PROFILE_ID}, {"$addToSet": {"lesson_days": today.isoformat()}})

    profile = await _profile(db)
    earned = []
    if await award_badge(db, BADGE_FIRST_LESSON):
        earned.append(BADGE_FIRST_LESSON)
    if compute_streak(profile.get("lesson_days"), today) >= 5 and await award_badge(db, BADGE_STREAK_5):
        earned.append(BADGE_STREAK_5)
    if subject_topics:
        done = await db.progress.count_documents(
            {"subject": subject, "topic": {"$in": list(subject_topics)}, "lesson_completed": True})
        if done >= len(subject_topics) and await award_badge(db, BADGE_SUBJECT_MASTER):
            earned.append(BADGE_SUBJECT_MASTER)
    info = level_info(total)
    return {"xp_earned": xp, "new_total_xp": total, "level": info["level"],
            "badge_earned": earned[0] if earned else None, "badges_earned": earned,
            "confetti": bool(earned) or first_time}


async def record_quiz_answer(db, subject, topic, correct: bool) -> int:
    inc = {"quiz_attempts": 1, "quiz_correct": 1 if correct else 0}
    xp = XP_QUIZ_CORRECT if correct else 0
    if xp:
        inc["total_xp"] = xp
    await db.progress.update_one(
        {"subject": subject, "topic": topic},
        {"$inc": inc, "$set": {"last_quiz_at": _now().isoformat(), "last_active": _now().isoformat()},
         "$setOnInsert": {"started_at": _now().isoformat()}},
        upsert=True)
    if xp:
        await add_xp(db, xp, "quiz_correct", subject, topic)
    return xp


async def record_perfect_quiz(db, subject, topic) -> dict:
    await add_xp(db, XP_PERFECT_QUIZ, "perfect_quiz", subject, topic)
    badge = BADGE_PERFECT_QUIZ if await award_badge(db, BADGE_PERFECT_QUIZ) else None
    return {"xp": XP_PERFECT_QUIZ, "badge": badge}


async def get_student_stats(db) -> dict:
    profile = await _profile(db)
    total_xp = int(profile.get("total_xp", 0))
    docs = await db.progress.find({}).to_list(2000)
    attempts = sum(d.get("quiz_attempts", 0) for d in docs)
    correct = sum(d.get("quiz_correct", 0) for d in docs)
    recent = await db.activity_log.find({}, {"_id": 0}).sort("created_at", -1).to_list(10)
    return {
        "total_xp": total_xp,
        **level_info(total_xp),
        "streak_days": compute_streak(profile.get("lesson_days"), _now().date()),
        "lessons_complete": sum(1 for d in docs if d.get("lesson_completed")),
        "quiz_attempts": attempts,
        "quiz_correct_pct": round(correct * 100 / attempts) if attempts else 0,
        "badges": profile.get("badges", []),
        "recent_activity": recent,
    }
