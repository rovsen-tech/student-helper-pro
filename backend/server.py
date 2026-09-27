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


class ChatRequest(BaseModel):
    book_id: Optional[str] = None
    message: str
    lang: str = "az"


class TTSRequest(BaseModel):
    text: str
    lang: str = "az"
    speed: float = 1.0


def tutor_system_message(lang: str, book: Optional[dict]) -> str:
    lang_name = "Azərbaycan dilində" if lang == "az" else "Türkçe"
    base = (
        f"Sən 'Ağıllı Müəllim' adlı çox mehriban, səbirli və həvəsləndirici bir müəllimsən. "
        f"11-14 yaşlı bir uşağa dərs izah edirsən. Uşağın gözləri zəifdir, ona görə cavabların qısa, "
        f"aydın və başa düşülən olsun. HƏMİŞƏ {lang_name} cavab ver. "
        f"Çətin anlayışları gündəlik həyatdan sadə bənzətmələrlə izah et (məsələn: hüceyrə nüvəsini məktəb direktoruna bənzət). "
        f"Uzun paraqraflar yox, qısa cümlələr işlət. Emoji istifadə etmə. "
        f"Cavabın sonunda uşağı ruhlandıran bir cümlə əlavə et və onu daha çox sual verməyə həvəsləndir."
    )
    if book:
        base += (
            f"\n\nHazırda bu dərsliyi öyrənirsiniz:\nBaşlıq: {book.get('title','')}\n"
            f"Mövzu: {book.get('subject','')}\nXülasə: {book.get('summary','')}\n"
            f"Əsas mövzular: {', '.join(book.get('key_topics', []))}\n"
            f"Detallı məzmun: {book.get('explanation','')[:4000]}\n"
            f"Uşağın suallarını bu dərsliyin məzmununa əsasən cavablandır."
        )
    return base


def make_chat(session_id: str, system_message: str) -> LlmChat:
    return LlmChat(api_key=EMERGENT_KEY, session_id=session_id,
                   system_message=system_message).with_model(MODEL_PROVIDER, MODEL_NAME)


@api_router.get("/")
async def root():
    return {"message": "Ağıllı Müəllim hazırdır"}


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
    session_id = f"chat-{req.book_id or 'general'}"
    sysmsg = tutor_system_message(req.lang, book)

    history = await db.messages.find({"session_id": session_id}).sort("created_at", 1).to_list(20)

    chat = make_chat(session_id, sysmsg)

    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "session_id": session_id, "role": "user",
        "content": req.message, "created_at": datetime.now(timezone.utc).isoformat(),
    })

    context = ""
    if history:
        recent = history[-6:]
        context = "Əvvəlki söhbət:\n" + "\n".join(
            f"{'Uşaq' if m['role']=='user' else 'Müəllim'}: {m['content']}" for m in recent) + "\n\nİndiki sual: "

    async def gen():
        full = ""
        try:
            async for ev in chat.stream_message(UserMessage(text=context + req.message)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'delta': ' (Bağışla, bir problem oldu, yenidən cəhd et.)'})}\n\n"
        await db.messages.insert_one({
            "id": str(uuid.uuid4()), "session_id": session_id, "role": "assistant",
            "content": full, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api_router.get("/messages/{book_id}")
async def get_messages(book_id: str):
    session_id = f"chat-{book_id or 'general'}"
    docs = await db.messages.find({"session_id": session_id}).sort("created_at", 1).to_list(200)
    return [{"role": d["role"], "content": d["content"], "id": d["id"]} for d in docs]


def clean_for_tts(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"[*_#>~|]", "", text)
    return re.sub(r"\s+", " ", text).strip()


@api_router.post("/tts")
async def tts(req: TTSRequest):
    text = clean_for_tts(req.text)[:4000]
    if not text:
        raise HTTPException(400, "Mətn boşdur")
    speed = max(0.5, min(2.0, req.speed))
    key = hashlib.sha256(f"{text}|{speed}|coral".encode()).hexdigest()
    cached = await db.tts_cache.find_one({"key": key})
    if cached and cached.get("storage_path"):
        try:
            audio = get_object(cached["storage_path"])
            return Response(content=audio, media_type="audio/mpeg",
                            headers={"Cache-Control": "public, max-age=31536000"})
        except Exception:
            pass
    try:
        engine = OpenAITextToSpeech(api_key=EMERGENT_KEY)
        audio = await engine.generate_speech(text=text, model="tts-1", voice="coral", speed=speed)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(500, "Səs yaradıla bilmədi")
    spath = f"{APP_NAME}/tts/{key}.mp3"
    try:
        put_object(spath, audio, "audio/mpeg")
        await db.tts_cache.insert_one({"key": key, "storage_path": spath})
    except Exception as e:
        logger.error(f"TTS cache store failed: {e}")
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Cache-Control": "public, max-age=31536000"})


SAMPLE_BOOKS = [
    {
        "title": "Hüceyrə — Canlıların Ən Kiçik Kərpici",
        "subject": "Biologiya", "grade": "6-cı sinif",
        "summary": "Bütün canlılar hüceyrələrdən qurulub. Hüceyrənin hissələri və vəzifələri haqqında öyrənirik.",
        "key_topics": ["Hüceyrə nüvəsi", "Sitoplazma", "Hüceyrə membranı", "Bitki və heyvan hüceyrələri"],
        "explanation": "Təsəvvür et ki, hüceyrə balaca bir məktəbdir. Nüvə məktəbin direktorudur — hər şeyi idarə edir. Membran isə məktəbin darvazasıdır: kimin girib-çıxacağına nəzarət edir. Sitoplazma məktəbin dəhlizləri kimidir, hər şey orada üzür. Bədənimizdə milyardlarla belə balaca 'məktəb' var və hamısı birlikdə işləyir!",
    },
    {
        "title": "Günəş Sistemi və Planetlər",
        "subject": "Təbiət elmləri", "grade": "6-cı sinif",
        "summary": "Günəş və onun ətrafında fırlanan 8 planet haqqında maraqlı məlumatlar.",
        "key_topics": ["Günəş", "8 planet", "Yer kürəsi", "Ay və peyklər"],
        "explanation": "Günəş sistemi böyük bir ailə kimidir. Günəş ata kimidir — ən böyük və isti. 8 planet isə uşaqlar kimi onun ətrafında dövrə vurur. Yer kürəsi bizim evimizdir və üzərində su olan yeganə planetdir. Merkuri Günəşə ən yaxın, ona görə çox istidir; Neptun ən uzaq, ona görə çox soyuqdur!",
    },
    {
        "title": "Kəsrlər və Faizlər",
        "subject": "Riyaziyyat", "grade": "6-cı sinif",
        "summary": "Bütövü hissələrə bölmək — kəsrlər və faizlərlə gündəlik hesablamalar.",
        "key_topics": ["Kəsr nədir", "Kəsrləri toplamaq", "Faiz hesablamaq", "Onluq kəsrlər"],
        "explanation": "Bir pizza təsəvvür et. Onu 4 bərabər hissəyə böldün — hər hissə 1/4-dür. 2 hissə yesən, 2/4 yəni yarısını yemisən! Faiz isə 'yüzdə neçə' deməkdir. 50% həmişə yarısı deməkdir. Riyaziyyat həyatda hər yerdədir — hətta pizza böləndə belə!",
    },
    {
        "title": "Qədim Şumer Mədəniyyəti",
        "subject": "Tarix", "grade": "6-cı sinif",
        "summary": "İlk yazını icad edən, şəhərlər quran qədim Şumerlilər haqqında.",
        "key_topics": ["Mixi yazı", "İlk şəhərlər", "Ziqquratlar", "Kənd təsərrüfatı"],
        "explanation": "Təxminən 5000 il əvvəl Şumerlilər yaşayırdı. Onlar dünyada ilk yazını — mixi yazını icad etdilər! Gilin üzərinə çubuqla işarələr yazırdılar. Böyük məbədlər olan ziqquratlar tikirdilər — nəhəng pilləkənli qüllələr kimi. Onlar həm də təkəri icad etdilər. Onlar olmasaydı, bəlkə bu gün yaza bilməzdik!",
    },
]


@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    for sb in SAMPLE_BOOKS:
        exists = await db.books.find_one({"title": sb["title"]})
        if not exists:
            b = Book(is_sample=True, **sb)
            doc = b.model_dump()
            doc["is_deleted"] = False
            await db.books.insert_one(doc)
    logger.info("Sample books seeded")


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
