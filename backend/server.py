from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import json
import hashlib
import logging
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone

import requests
from emergentintegrations.llm.chat import (
    LlmChat, UserMessage, FileContentWithMimeType, TextDelta, StreamDone,
)
from emergentintegrations.llm.openai import OpenAITextToSpeech

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
MODEL_PROVIDER = "gemini"
MODEL_NAME = "gemini-3.1-pro-preview"

# ---- Object storage ----
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "gozum-bilgim"
storage_key = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def init_storage(force: bool = False):
    global storage_key
    if storage_key and not force:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type},
                            data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> bytes:
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content


app = FastAPI()
api_router = APIRouter(prefix="/api")


# ---- Models ----
class Book(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    subject: str = ""
    grade: str = ""
    summary: str = ""
    key_topics: List[str] = []
    explanation: str = ""
    storage_path: Optional[str] = None
    is_sample: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


PROVENANCE = ("SOURCE", "DERIVED", "GENERATED")
CONTENT_TYPES = ("explanation", "definition", "rule", "worked_example", "task",
                 "problem", "answer", "investigation", "think", "note", "summary", "glossary")


class StructuredContent(BaseModel):
    type: str          # one of CONTENT_TYPES
    provenance: str = "SOURCE"   # one of PROVENANCE
    text: str
    normalized_text: str = ""
    original_text: str = ""
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    source_page: Optional[int] = None


class Lesson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    textbook_id: str
    section_id: str
    order: int = 0
    number: str = ""
    title: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    content: List[StructuredContent] = []


class Section(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    textbook_id: str
    order: int = 0
    title: str


class Textbook(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject_id: str
    title: str
    grade: str = ""
    provenance: str = "SOURCE"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatRequest(BaseModel):
    book_id: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    message: str = ""
    lang: str = "az"
    explain: bool = False
    stage: Optional[str] = None
    lesson_id: Optional[str] = None
    student_id: Optional[str] = None


def session_key(book_id=None, subject=None, topic=None, student_id=None):
    sid = (student_id or "anon")
    if book_id:
        return f"{sid}-book-{book_id}"
    if subject and topic:
        return f"{sid}-lesson-" + hashlib.sha256(f"{subject}|{topic}".encode()).hexdigest()[:12]
    return f"{sid}-general"


async def record_activity(subject, topic, is_question):
    now = datetime.now(timezone.utc).isoformat()
    update = {"$set": {"last_active": now}, "$setOnInsert": {"started_at": now}}
    if is_question:
        update["$inc"] = {"question_count": 1}
    else:
        update["$set"]["explained"] = True
    await db.progress.update_one({"subject": subject, "topic": topic}, update, upsert=True)


class TTSRequest(BaseModel):
    text: str
    lang: str = "az"
    speed: float = 1.0
    voice: str = "coral"


def tutor_system_message(lang: str, book=None, subject=None, topic=None, lesson_source=None) -> str:
    lang_name = "Azərbaycan dilində" if lang == "az" else "Türkçe"
    base = (
        f"Sən 'Ağıllı Müəllim' adlı diqqətli, səbirli və mehriban şəxsi müəllimsən — sadəcə chatbot deyilsən. "
        f"Azərbaycanın 5-ci sinif milli kurikuluna uyğun, 10-11 yaşlı şagirdə dərs keçirsən. "
        f"Şagirdin gözləri zəifdir: mətn qısa olsun, əsas məlumat sözlə çatsın. HƏMİŞƏ {lang_name} təbii, "
        f"yaşına uyğun, sadə dildə danış. Termini deyəndə onu adi sözlə izah et və bir nümunə ver.\n"
        f"QAYDALAR:\n"
        f"1) Uzun monoloq qurma. Bir kiçik fikir → qısa izah → (lazımsa) nümunə → şagirdə kiçik tapşırıq. 2-4 qısa cümlə kifayətdir.\n"
        f"2) 'Başa düşdün?' deyə soruşma. Anlamağı belə yoxla: 'Bunu öz sözlərinlə necə deyərdin?', 'Növbəti addım nədir?', 'Bunlardan hansı doğrudur, niyə?', 'İndi buna oxşar birini sən həll et.'\n"
        f"3) Sual verəndə cavabı dərhal özün demə — şagirdə düşünməyə imkan ver.\n"
        f"4) Minimum kömək: şagird özü edə bilirsə qarışma; kiçik ipucu kifayətdirsə, bütöv həlli vermə.\n"
        f"5) Səhv olanda 'Yanlışdır' demə. Əvvəl düzgün hissəni qeyd et, sonra fikrin hansı addımda dəyişdiyini tap, ən kiçik ipucu ver, şagird yenidən sınasın.\n"
        f"6) Şagird 'başa düşmədim' desə, eyni cavabı təkrarlama — izah üsulunu dəyiş: daha sadə dil, konkret nümunə, gündəlik bənzətmə, kiçik ön-biliyə qayıt.\n"
        f"7) Boş yerə tərifləmə. Tərif konkret və qazanılmış olsun (məs: 'İpucu olmadan həll etdin'). 'Əla/Möhtəşəm' kimi boş sözləri təkrarlama.\n"
        f"8) Şagird asanlıqla həll edirsə çətinliyi artır; çətinlik çəkirsə sadələşdir və ön-biliyi bərpa et. Məqsəd — şagirdin müstəqilliyi.\n"
        f"Emoji işlətmə. Hər şey sakit, aydın və başa düşülən olsun."
    )
    if subject:
        base += f"\n\nHazırkı fənn: {subject}."
        if topic:
            base += f" Mövzu: «{topic}». Cavablarını bu fənn və mövzu ətrafında saxla."
    if lesson_source:
        base += (
            "\n\nDƏRSLİK MƏNBƏYİ (ƏSAS HƏQİQƏT — yalnız buna əsaslan, kənardan məlumat və ya "
            "səhifə nömrəsi uydurma):\n" + lesson_source[:3500]
        )
    if book:
        base += (
            f"\n\nHazırda bu dərsliyi öyrənirsiniz:\nBaşlıq: {book.get('title','')}\n"
            f"Xülasə: {book.get('summary','')}\n"
            f"Əsas mövzular: {', '.join(book.get('key_topics', []))}\n"
            f"Detallı məzmun: {book.get('explanation','')[:4000]}\n"
            f"Şagirdin suallarını bu dərsliyin məzmununa əsasən cavablandır."
        )
    return base


def make_chat(session_id: str, system_message: str) -> LlmChat:
    return LlmChat(api_key=EMERGENT_KEY, session_id=session_id,
                   system_message=system_message).with_model(MODEL_PROVIDER, MODEL_NAME)


@api_router.get("/")
async def root():
    return {"message": "Ağıllı Dərs hazırdır"}


@api_router.get("/subjects")
async def list_subjects():
    return SUBJECTS


@api_router.get("/textbooks/{subject}")
async def get_textbooks(subject: str):
    tbs = await db.textbooks.find({"subject_id": subject}).to_list(100)
    result = []
    for tb in tbs:
        secs = await db.sections.find({"textbook_id": tb["id"]}).sort("order", 1).to_list(100)
        sections = []
        for s in secs:
            count = await db.lessons.count_documents({"section_id": s["id"]})
            sections.append({"id": s["id"], "title": s["title"],
                             "order": s.get("order", 0), "lesson_count": count})
        result.append({"id": tb["id"], "subject_id": tb["subject_id"], "title": tb["title"],
                       "grade": tb.get("grade", ""), "provenance": tb.get("provenance", "SOURCE"),
                       "sections": sections})
    return result


@api_router.get("/lessons/{textbook_id}/{section_id}")
async def get_lessons(textbook_id: str, section_id: str):
    docs = await db.lessons.find({"textbook_id": textbook_id, "section_id": section_id}).sort("order", 1).to_list(200)
    return [Lesson(**{k: v for k, v in d.items() if k != "_id"}).model_dump() for d in docs]


@api_router.get("/books", response_model=List[Book])
async def list_books():
    docs = await db.books.find({"is_deleted": {"$ne": True}}).sort("created_at", 1).to_list(1000)
    return [Book(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]


@api_router.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: str):
    d = await db.books.find_one({"id": book_id, "is_deleted": {"$ne": True}})
    if not d:
        raise HTTPException(404, "Kitab tapılmadı")
    return Book(**{k: v for k, v in d.items() if k != "_id"})


@api_router.post("/books/upload", response_model=Book)
async def upload_book(file: UploadFile = File(...), lang: str = Form("az")):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Yalnız PDF faylları qəbul olunur")
    data = await file.read()
    path = f"{APP_NAME}/uploads/{uuid.uuid4()}.pdf"
    try:
        put_object(path, data, "application/pdf")
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(500, "Fayl yüklənə bilmədi")

    # Analyze PDF with Gemini
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(data)
    tmp.close()
    analysis = {}
    try:
        chat = make_chat(f"analyze-{uuid.uuid4()}",
                         "Sən təhsil məzmununu təhlil edən bir köməkçisən. Yalnız JSON qaytar.")
        prompt = (
            "Bu PDF dərsliyi təhlil et və 11-14 yaşlı uşaq üçün sadələşdir. "
            "SADƏCƏ bu formatda düzgün JSON qaytar (başqa mətn yox), dəyərlər "
            + ("Azərbaycan dilində" if lang == "az" else "Türkçe") + " olsun:\n"
            '{"title": "qısa başlıq", "subject": "fənn", "grade": "sinif", '
            '"summary": "2-3 cümləlik xülasə", "key_topics": ["mövzu1","mövzu2","mövzu3"], '
            '"explanation": "uşağa uyğun sadə və maraqlı izah, bənzətmələrlə, 300-500 söz"}'
        )
        pdf_file = FileContentWithMimeType(file_path=tmp.name, mime_type="application/pdf")
        buf = ""
        async for ev in chat.stream_message(UserMessage(text=prompt, file_contents=[pdf_file])):
            if isinstance(ev, TextDelta):
                buf += ev.content
            elif isinstance(ev, StreamDone):
                break
        m = re.search(r"\{.*\}", buf, re.DOTALL)
        if m:
            analysis = json.loads(m.group(0))
    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    book = Book(
        title=analysis.get("title") or file.filename.replace(".pdf", ""),
        subject=analysis.get("subject", ""),
        grade=analysis.get("grade", ""),
        summary=analysis.get("summary", ""),
        key_topics=analysis.get("key_topics", []) or [],
        explanation=analysis.get("explanation", ""),
        storage_path=path,
    )
    doc = book.model_dump()
    doc["is_deleted"] = False
    await db.books.insert_one(doc)
    return book


@api_router.post("/chat")
async def chat_stream(req: ChatRequest):
    book = None
    if req.book_id:
        book = await db.books.find_one({"id": req.book_id})
    session_id = session_key(req.book_id, req.subject, req.topic, req.student_id)
    lesson_source = None
    if req.lesson_id:
        ldoc = await db.lessons.find_one({"id": req.lesson_id})
        if ldoc:
            parts = []
            for c in ldoc.get("content", []):
                if c.get("provenance") == "SOURCE" and c.get("type") != "answer":
                    parts.append(c.get("normalized_text") or c.get("text", ""))
            pref = ""
            if ldoc.get("page_start"):
                pref = f"(səhifə {ldoc['page_start']}-{ldoc.get('page_end', ldoc['page_start'])}) "
            lesson_source = pref + "\n".join(p for p in parts if p)
    sysmsg = tutor_system_message(req.lang, book, req.subject, req.topic, lesson_source)

    history = await db.messages.find({"session_id": session_id}).sort("created_at", 1).to_list(20)
    chat = make_chat(session_id, sysmsg)

    if req.explain:
        user_text = (f"«{req.topic}» mövzusunu 5-ci sinif şagirdinə uyğun, maraqlı və sadə "
                     f"şəkildə, gündəlik nümunələrlə izah et. Qısa və aydın saxla. "
                     f"Sonda şagirdə de ki, indi növbə onundur və bu mövzunu öz sözləri ilə danışmalıdır.")
    elif req.stage == "recall":
        if req.message:
            await db.messages.insert_one({
                "id": str(uuid.uuid4()), "session_id": session_id, "role": "user",
                "content": req.message, "created_at": datetime.now(timezone.utc).isoformat(),
            })
        user_text = (f"Şagird «{req.topic}» mövzusunu öz sözləri ilə belə izah etdi:\n«{req.message}»\n"
                     f"Doğru və yaxşı hissələri qısaca tərif et, varsa səhvləri çox mehribanca düzəlt və "
                     f"düzgün formasını de. Sonra ona de: «Əla! İndi sənə bu mövzudan bir neçə sual verəcəm, hazırsan?»")
    elif req.stage == "quiz_next":
        user_text = (f"Şagirdə «{req.topic}» mövzusundan BİR qısa və sadə sual ver. "
                     f"Əvvəl verdiyin sualları təkrar etmə. Yalnız sualı yaz, cavabı yazma.")
    elif req.stage == "quiz_answer":
        if req.message:
            await db.messages.insert_one({
                "id": str(uuid.uuid4()), "session_id": session_id, "role": "user",
                "content": req.message, "created_at": datetime.now(timezone.utc).isoformat(),
            })
        user_text = (f"Bu, verdiyin sonuncu suala şagirdin cavabıdır:\n«{req.message}»\n"
                     f"Əgər cavab doğrudursa, onu təriflə və dərhal növbəti qısa sualı ver. "
                     f"Əgər cavab səhvdirsə və ya şagird bilmədiyini deyirsə, həmin mövzunu müəllimdən daha "
                     f"yaxşı, daha sadə şəkildə, gündəlik nümunə ilə yenidən izah et, sonra asan bir sual ver. "
                     f"Təxminən 3 sualdan sonra dərsi ürəkləndirici sözlərlə bitir.")
    else:
        user_text = req.message
        await db.messages.insert_one({
            "id": str(uuid.uuid4()), "session_id": session_id, "role": "user",
            "content": req.message, "created_at": datetime.now(timezone.utc).isoformat(),
        })

    context = ""
    if history and not req.explain:
        recent = history[-8:]
        context = "Əvvəlki söhbət:\n" + "\n".join(
            f"{'Şagird' if m['role']=='user' else 'Müəllim'}: {m['content']}" for m in recent) + "\n\nTapşırıq: "

    if req.subject and req.topic:
        a_subject, a_topic = req.subject, req.topic
    elif book:
        a_subject, a_topic = "Yüklənən kitablar", book.get("title", "Kitab")
    else:
        a_subject, a_topic = "Ümumi söhbət", "Suallar"
    await record_activity(a_subject, a_topic, (not req.explain) and bool(req.message))

    async def gen():
        full = ""
        errored = False
        try:
            async for ev in chat.stream_message(UserMessage(text=context + user_text)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"Chat error: {e}")
            errored = True
        if errored or not full.strip():
            yield f"data: {json.dumps({'error': True})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return
        await db.messages.insert_one({
            "id": str(uuid.uuid4()), "session_id": session_id, "role": "assistant",
            "content": full, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api_router.get("/messages")
async def get_messages(book_id: str = None, subject: str = None, topic: str = None, student_id: str = None):
    session_id = session_key(book_id, subject, topic, student_id)
    docs = await db.messages.find({"session_id": session_id}).sort("created_at", 1).to_list(200)
    return [{"role": d["role"], "content": d["content"], "id": d["id"]} for d in docs]


@api_router.get("/progress")
async def get_progress():
    docs = await db.progress.find({}).sort("last_active", -1).to_list(1000)
    by_subject = {}
    total_q = 0
    for d in docs:
        s = d["subject"]
        by_subject.setdefault(s, {"subject": s, "lessons": [], "total_questions": 0, "last_active": d.get("last_active")})
        by_subject[s]["lessons"].append({
            "topic": d["topic"], "question_count": d.get("question_count", 0),
            "explained": d.get("explained", False), "last_active": d.get("last_active"),
        })
        by_subject[s]["total_questions"] += d.get("question_count", 0)
        total_q += d.get("question_count", 0)
    return {
        "total_questions": total_q,
        "subjects_studied": len(by_subject),
        "lessons_started": len(docs),
        "last_active": docs[0].get("last_active") if docs else None,
        "by_subject": list(by_subject.values()),
    }


def clean_for_tts(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    # speech-prep: verbalize common math for natural Azerbaijani speech
    text = re.sub(r"(\d+)\s*%", r"\1 faiz", text)
    text = re.sub(r"(\d+)\s*/\s*(\d+)", r"\1 bölü \2", text)
    text = text.replace("×", " vur ").replace("÷", " bölü ").replace("=", " bərabərdir ").replace("°", " dərəcə ")
    text = re.sub(r"[*_#>~|]", "", text)
    return re.sub(r"\s+", " ", text).strip()


@api_router.post("/tts")
async def tts(req: TTSRequest):
    text = clean_for_tts(req.text)[:4000]
    if not text:
        raise HTTPException(400, "Mətn boşdur")
    speed = max(0.5, min(2.0, req.speed))
    voice = req.voice if req.voice in ("coral", "nova") else "coral"
    key = hashlib.sha256(f"{text}|{speed}|{voice}".encode()).hexdigest()
    cached = await db.tts_cache.find_one({"key": key})
    if cached and cached.get("storage_path"):
        try:
            audio = get_object(cached["storage_path"])
            return Response(content=audio, media_type="audio/mpeg",
                            headers={"Cache-Control": "public, max-age=31536000"})
        except Exception:
            pass
    audio = None
    try:
        engine = OpenAITextToSpeech(api_key=EMERGENT_KEY)
        audio = await engine.generate_speech(text=text, model="tts-1", voice=voice, speed=speed)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(500, "Səs yaradıla bilmədi")
    if not audio:
        raise HTTPException(500, "Səs yaradıla bilmədi")
    spath = f"{APP_NAME}/tts/{key}.mp3"
    try:
        put_object(spath, audio, "audio/mpeg")
        await db.tts_cache.insert_one({"key": key, "storage_path": spath})
    except Exception as e:
        logger.error(f"TTS cache store failed: {e}")
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Cache-Control": "public, max-age=31536000"})


SUBJECTS = [
    {"id": "azdili", "name": "Azərbaycan dili", "icon": "BookText", "color": "#DC2626",
     "description": "Ana dilimiz — səslər, sözlər, cümlələr və mətnlər.",
     "topics": ["Səslər və hərflər", "Sözün tərkibi", "İsim", "Sifət", "Fel", "Cümlə üzvləri", "Mətn və nitq mədəniyyəti"]},
    {"id": "riyaziyyat", "name": "Riyaziyyat", "icon": "Calculator", "color": "#2563EB",
     "description": "Ədədlər, hesablamalar və həndəsə dünyası.",
     "topics": ["Natural ədədlər", "Adi kəsrlər", "Onluq kəsrlər", "Faiz", "Həndəsi fiqurlar", "Ölçü vahidləri", "Sadə tənliklər"]},
    {"id": "tebiet", "name": "Təbiət", "icon": "Leaf", "color": "#16A34A",
     "description": "Canlılar, bitkilər, planetimiz və kainat.",
     "topics": ["Canlılar aləmi", "Bitkilər", "Heyvanlar", "Su, hava və torpaq", "Günəş sistemi", "Ekologiya və təbiətin qorunması"]},
    {"id": "informatika", "name": "İnformatika", "icon": "Laptop", "color": "#0891B2",
     "description": "Kompüter, informasiya və təhlükəsiz internet.",
     "topics": ["Kompüterin hissələri", "İnformasiya nədir", "Fayl və qovluqlar", "İnternet", "Təhlükəsizlik qaydaları", "Sadə alqoritmlər"]},
    {"id": "ingilis", "name": "İngilis dili", "icon": "Languages", "color": "#7C3AED",
     "description": "Learn English — words, phrases and fun.",
     "topics": ["Alphabet and sounds", "Greetings", "Family members", "Numbers and colours", "Daily routine", "Animals and nature"]},
    {"id": "tarix", "name": "Tarix", "icon": "Landmark", "color": "#B45309",
     "description": "Keçmişimiz, qədim dövlətlər və mədəniyyət.",
     "topics": ["Qədim insanlar", "İlk şəhərlər və dövlətlər", "Azərbaycanın qədim tarixi", "Tarixi abidələr", "Tarixi mənbələr"]},
    {"id": "musiqi", "name": "Musiqi", "icon": "Music", "color": "#DB2777",
     "description": "Səslər, notlar və Azərbaycan musiqisi.",
     "topics": ["Musiqi səsləri", "Notlar", "Musiqi alətləri", "Azərbaycan xalq musiqisi", "Muğam", "Ritm və mahnı"]},
    {"id": "tesviri", "name": "Təsviri incəsənət", "icon": "Palette", "color": "#EA580C",
     "description": "Rənglər, rəsm və xalq sənəti.",
     "topics": ["Rənglər aləmi", "Rəsm növləri", "Kompozisiya", "Milli naxışlar", "Xalça sənəti", "Heykəltəraşlıq"]},
    {"id": "texnologiya", "name": "Texnologiya", "icon": "Wrench", "color": "#4B5563",
     "description": "Əl işləri, materiallar və sağlam qida.",
     "topics": ["Materiallar", "Əl işləri", "Qida və sağlamlıq", "Bitki becərmə", "Təhlükəsizlik qaydaları"]},
    {"id": "fiziki", "name": "Fiziki tərbiyə", "icon": "Dumbbell", "color": "#059669",
     "description": "Hərəkət, idman və sağlam həyat tərzi.",
     "topics": ["Gimnastika", "Atletika", "İdman oyunları", "Sağlam həyat tərzi", "Bədən quruluşu"]},
]


async def seed_textbooks():
    tb_id = "tb-riyaziyyat-5"
    if await db.textbooks.find_one({"id": tb_id}):
        return
    tb = Textbook(id=tb_id, subject_id="riyaziyyat",
                  title="Riyaziyyat 5 (nümunə struktur)", grade="5-ci sinif", provenance="SOURCE")
    await db.textbooks.insert_one(tb.model_dump())
    sections = [
        Section(id="sec-natural", textbook_id=tb_id, order=1, title="Natural ədədlər"),
        Section(id="sec-fractions", textbook_id=tb_id, order=2, title="Adi kəsrlər"),
    ]
    for s in sections:
        await db.sections.insert_one(s.model_dump())

    def ph(type_, label):
        # Placeholder only — NO fabricated textbook content. Real text will come from PDF ingestion.
        return StructuredContent(type=type_, provenance="SOURCE",
                                 text=f"[PLACEHOLDER — {label}. Real məzmun dərslik PDF-dən gələcək.]")

    lessons = [
        Lesson(id="les-natural-1", textbook_id=tb_id, section_id="sec-natural", order=1,
               title="Natural ədədlərin oxunuşu və yazılışı",
               content=[ph("explanation", "izah"), ph("definition", "tərif"), ph("rule", "qayda"),
                        ph("worked_example", "həll olunmuş nümunə"), ph("task", "tapşırıq"),
                        ph("problem", "məsələ"), ph("answer", "cavab")]),
        Lesson(id="les-natural-2", textbook_id=tb_id, section_id="sec-natural", order=2,
               title="Natural ədədlərin müqayisəsi",
               content=[ph("explanation", "izah"), ph("definition", "tərif"),
                        ph("worked_example", "həll olunmuş nümunə"), ph("task", "tapşırıq")]),
        Lesson(id="les-fractions-1", textbook_id=tb_id, section_id="sec-fractions", order=1,
               title="Kəsr anlayışı",
               content=[ph("explanation", "izah"), ph("definition", "tərif"), ph("rule", "qayda"),
                        ph("worked_example", "həll olunmuş nümunə"), ph("task", "tapşırıq"),
                        ph("problem", "məsələ"), ph("answer", "cavab")]),
        Lesson(id="les-fractions-2", textbook_id=tb_id, section_id="sec-fractions", order=2,
               title="Kəsrlərin müqayisəsi",
               content=[ph("explanation", "izah"), ph("worked_example", "həll olunmuş nümunə"),
                        ph("task", "tapşırıq"), ph("answer", "cavab")]),
    ]
    for lesson in lessons:
        await db.lessons.insert_one(lesson.model_dump())
    logger.info("Riyaziyyat textbook foundation seeded")


@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    await db.books.delete_many({"is_sample": True})
    await db.textbooks.delete_many({"id": "tb-riyaziyyat-5"})
    await db.sections.delete_many({"textbook_id": "tb-riyaziyyat-5"})
    await db.lessons.delete_many({"textbook_id": "tb-riyaziyyat-5"})
    logger.info("Startup complete")


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
