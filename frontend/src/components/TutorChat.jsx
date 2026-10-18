import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowLeft, Send, Mic, Volume2, Square, Loader2, GraduationCap, Sparkles, PencilLine, ListChecks, BookOpen, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { useTTS } from "../hooks/useTTS";
import { SmartNotes } from "./SmartNotes";
import { QuizCard, Confetti } from "./QuizCard";
import { ReadingMode } from "./ReadingMode";
import { ReviewQuestions } from "./ReviewQuestions";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Zəif görən uşaq üçün ekranda xam Markdown simvolları (**, #, `) göstərilmir; mətn özü dəyişmir.
export const cleanForDisplay = (text) =>
  String(text || "")
    .replace(/\*\*|__|`+/g, "")
    .replace(/^\s*#{1,6}\s+/gm, "")
    .replace(/^\s*[*+]\s+/gm, "• ");

const Waveform = () => (
  <div className="flex items-end gap-1 h-6">
    {[0, 1, 2, 3, 4].map((i) => (
      <span key={i} className="wave-bar w-1.5 bg-white rounded-full accent-fg"
        style={{ background: "currentColor", animationDelay: `${i * 0.12}s`, height: "40%" }} />
    ))}
  </div>
);

export const TutorChat = ({ t, lang, ctx, speed, onBack, studentId }) => {
  const book = ctx.kind === "book" ? ctx.book : null;
  const subject = ctx.kind === "lesson" ? ctx.subject : null;
  const topic = ctx.kind === "lesson" ? ctx.topic : null;
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [listening, setListening] = useState(false);
  const [stage, setStage] = useState(null);
  const { speak, stop, speakingId, loading } = useTTS(lang, speed);
  const scrollRef = useRef(null);
  const recRef = useRef(null);
  const micHeldRef = useRef(false);
  const micTranscriptRef = useRef("");
  const inputRef = useRef(null);
  const autoSpokeRef = useRef(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [notesData, setNotesData] = useState(null);
  const [notesLoading, setNotesLoading] = useState(false);
  const [readingText, setReadingText] = useState(null);
  const [quiz, setQuiz] = useState(null);
  const [quizLoading, setQuizLoading] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [celebrate, setCelebrate] = useState(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  const openReading = (text) => { stop(); setReadingText(text); };

  const completeLesson = async () => {
    if (!subject || !topic || completing) return;
    setCompleting(true);
    try {
      const res = await fetch(`${API}/progress/lesson-complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, topic }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStage("done");
      setCelebrate(data);
      if (data.first_time === false) toast.info("Bu dərs artıq bitirilib — təkrar üçün XP verilmir, amma təkrar etmək çox faydalıdır!");
      else toast.success(`+${data.xp_earned} XP · ${data.level}${data.badge_earned ? ` · 🏅 ${data.badge_earned}` : ""}`);
      setTimeout(() => setCelebrate(null), 3500);
    } catch (err) {
      console.error("Lesson complete failed", err);
      toast.error("Dərs qeyd oluna bilmədi");
    } finally { setCompleting(false); }
  };

  const startMiniQuiz = async () => {
    if (!subject || !topic || quizLoading) return;
    stop();
    setQuizLoading(true);
    try {
      const res = await fetch(`${API}/quiz/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, topic, lang, difficulty: "easy", n_questions: 5 }),
      });
      if (res.status === 429) {
        const d = await res.json().catch(() => ({}));
        toast.error(d.detail || "Bu gün üçün quiz limiti doldu. Sabah yenidən cəhd et!");
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setQuiz(await res.json());
    } catch (err) {
      console.error("Quiz generate failed", err);
      toast.error("Suallar hazırlana bilmədi, yenidən cəhd et");
    } finally { setQuizLoading(false); }
  };

  const generateNotes = async () => {
    setNotesOpen(true);
    setNotesLoading(true);
    try {
      const conversation = messages
        .filter((m) => m?.content)
        .slice(-100)
        .map((m) => ({ role: m.role, content: String(m.content).slice(0, 8000) }));
      const res = await fetch(`${BACKEND_URL}/api/notes/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lesson_id: book?.id || (subject && topic ? `${subject}|${topic}` : null),
          subject, topic, lang: "az", exam_mode: false, conversation,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setNotesData(await res.json());
    } catch (err) {
      console.error("Notes failed", err);
      toast.error("Qeydlər hazırlana bilmədi");
      setNotesOpen(false);
    } finally { setNotesLoading(false); }
  };

  const scrollDown = () => setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 50);

  const qs = () => {
    const p = new URLSearchParams();
    if (book) p.set("book_id", book.id);
    if (subject) { p.set("subject", subject); p.set("topic", topic); }
    return p.toString();
  };

  const readStream = async (res, aiId) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "", full = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const p of parts) {
        const line = p.replace(/^data: /, "").trim();
        if (!line) continue;
        try {
          const obj = JSON.parse(line);
          if (obj.delta) {
            full += obj.delta;
            setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, content: full } : x)));
            scrollDown();
          }
        } catch (err) { console.warn("SSE parse skipped", err); }
      }
    }
    return full;
  };

  const runAssistant = async (body, seedId) => {
    const aiId = seedId || `a${Date.now()}`;
    setMessages((m) => (seedId ? [{ role: "assistant", content: "", id: aiId }] : [...m, { role: "assistant", content: "", id: aiId }]));
    setStreaming(true);
    scrollDown();
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const full = await readStream(res, aiId);
      if (full) speak(full, aiId);
    } catch {
      toast.error("Xəta");
    } finally { setStreaming(false); scrollDown(); }
  };

  const streamExplain = async () => {
    await runAssistant({ subject, topic, lang, explain: true }, "explain");
    setStage("explained");
  };

  const startRecall = () => { setStage("recall_input"); inputRef.current?.focus(); };

  const startQuiz = async () => {
    setStage("quiz");
    await runAssistant({ subject, topic, lang, stage: "quiz_next" });
  };

  const initRef = useRef(null);
  useEffect(() => {
    const key = `${book?.id || ""}|${subject || ""}|${topic || ""}`;
    if (initRef.current === key) return;
    initRef.current = key;
    const load = async () => {
      if (subject && topic) { streamExplain(); return; }
      let hist = [];
      try {
        const res = await fetch(`${API}/messages?${qs()}`);
        hist = await res.json();
      } catch (err) { console.error("Failed to load messages", err); }
      if (hist.length > 0) { setMessages(hist); scrollDown(); return; }
      if (book) {
        setMessages([{ role: "assistant", content: book.explanation, id: "intro" }]);
        scrollDown();
      } else {
        setMessages([{ role: "assistant", content: t.welcome, id: "intro" }]);
        scrollDown();
      }
    };
    load();
    // eslint-disable-next-line
  }, [book?.id, subject, topic]);

  const send = useCallback(async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || streaming) return;
    stop();
    setInput("");
    const effStage = subject && topic
      ? (stage === "recall_input" ? "recall" : stage === "quiz" ? "quiz_answer" : undefined)
      : undefined;
    const userMsg = { role: "user", content: msg, id: `u${Date.now()}` };
    const aiId = `a${Date.now()}`;
    setMessages((m) => [...m, userMsg, { role: "assistant", content: "", id: aiId }]);
    setStreaming(true);
    scrollDown();
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: book?.id || null, subject, topic, message: msg, lang, stage: effStage }),
      });
      const full = await readStream(res, aiId);
      if (full) speak(full, aiId);
      if (effStage === "recall") setStage("recalled");
    } catch {
      toast.error("Xəta");
    } finally {
      setStreaming(false);
      scrollDown();
    }
  }, [input, streaming, book, subject, topic, lang, stage, speak, stop]);

  const startMic = (event) => {
    if (micHeldRef.current) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast.error(t.micError); return; }
    stop();
    event?.currentTarget.setPointerCapture?.(event.pointerId);
    micHeldRef.current = true;
    micTranscriptRef.current = "";
    setInput("");
    setListening(true);
    const startRecognition = () => {
      if (!micHeldRef.current) return;
      const rec = new SR();
      rec.lang = lang === "az" ? "az-AZ" : "tr-TR";
      rec.continuous = true;
      rec.interimResults = false;
      rec.onresult = (e) => {
        const transcript = Array.from(e.results)
          .slice(e.resultIndex)
          .filter((result) => result.isFinal)
          .map((result) => result[0].transcript.trim())
          .filter(Boolean)
          .join(" ");
        if (!transcript) return;
        micTranscriptRef.current = [micTranscriptRef.current, transcript].filter(Boolean).join(" ");
        setInput(micTranscriptRef.current);
      };
      rec.onerror = (e) => {
        if (e.error === "no-speech") return;
        micHeldRef.current = false;
        setListening(false);
        toast.error(t.micError);
      };
      rec.onend = () => {
        if (recRef.current === rec) recRef.current = null;
        if (micHeldRef.current) startRecognition();
        else setListening(false);
      };
      recRef.current = rec;
      try {
        rec.start();
      } catch {
        micHeldRef.current = false;
        recRef.current = null;
        setListening(false);
        toast.error(t.micError);
      }
    };
    startRecognition();
  };
  const stopMic = () => {
    micHeldRef.current = false;
    recRef.current?.stop();
    setListening(false);
  };

  const quicks = [t.q1, t.q2, t.q3];

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col" style={{ height: "calc(100vh - 76px)" }}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <button data-testid="chat-back-btn" onClick={onBack} aria-label={t.back}
          className="w-12 h-12 rounded-2xl bg-surface border-solid-2 flex items-center justify-center hover:bg-surface-2 transition-colors shrink-0">
          <ArrowLeft size={26} />
        </button>
        <div className="w-14 h-14 rounded-2xl bg-accent flex items-center justify-center shrink-0" style={{ color: "#fff" }}>
          <GraduationCap size={30} className="accent-fg" />
        </div>
        <div className="min-w-0">
          <h2 className="font-heading font-bold text-2xl truncate">{topic || (book ? book.title : t.general)}</h2>
          {subject && <p className="text-secondary text-base truncate">{subject}</p>}
          {book?.key_topics?.length > 0 && (
            <p className="text-secondary text-base truncate">{book.key_topics.join(" • ")}</p>
          )}
        </div>
        <button data-testid="notes-btn" onClick={generateNotes} disabled={streaming || notesLoading}
          className="ml-auto h-12 px-4 rounded-2xl bg-surface border-solid-2 font-bold text-lg hover:bg-surface-2 transition-colors shrink-0 disabled:opacity-50">
          📝 Qeydlər
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} data-testid="chat-messages" className="flex-1 overflow-y-auto space-y-4 pr-1 pb-2">
        {messages.map((m) => (
          <div key={m.id} className={`rise flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-3xl px-5 py-4 border-solid-2 ${m.role === "user" ? "bg-accent text-white accent-fg" : "bg-surface"}`}
              style={m.role === "user" ? { borderColor: "var(--accent)" } : {}}>
              <p className="text-xl whitespace-pre-wrap leading-relaxed">{m.content ? cleanForDisplay(m.content) : (streaming ? t.thinking : "")}</p>
              {m.role === "assistant" && m.content && (
                <button data-testid={`listen-btn-${m.id}`} onClick={() => (speakingId === m.id ? stop() : speak(m.content, m.id))}
                  className="mt-3 inline-flex items-center gap-2 h-11 px-4 rounded-2xl bg-surface-2 border-solid-2 font-bold text-lg hover:bg-accent hover:text-white transition-colors">
                  {speakingId === m.id ? (loading ? <Loader2 size={22} className="animate-spin" /> : <Square size={20} />) : <Volume2 size={22} />}
                  {speakingId === m.id ? t.stop : t.listen}
                </button>
              )}
              {m.role === "assistant" && m.content && (
                <button data-testid={`reading-btn-${m.id}`} onClick={() => openReading(m.content)} aria-label="Oxuma rejimi"
                  className="mt-3 ml-2 inline-flex items-center gap-2 h-11 px-4 rounded-2xl bg-surface-2 border-solid-2 font-bold text-lg hover:bg-accent hover:text-white transition-colors">
                  <BookOpen size={22} /> 📖 Oxu
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {notesOpen && (
        <div className="mt-3 max-h-80 overflow-y-auto">
          <SmartNotes notes={notesData} loading={notesLoading} onClose={() => setNotesOpen(false)} />
        </div>
      )}

      {/* Stage controls (lessons only) */}
      {subject && topic && stage && (
        <div data-testid="stage-indicator" className="flex flex-wrap items-center gap-2 text-base font-semibold mt-3">
          <span className={`px-3 py-1 rounded-full ${stage === "explained" ? "bg-accent text-white accent-fg" : "bg-surface-2 text-secondary"}`}>1. {t.stageExplain}</span>
          <span className={`px-3 py-1 rounded-full ${(stage === "recall_input" || stage === "recalled") ? "bg-accent text-white accent-fg" : "bg-surface-2 text-secondary"}`}>2. {t.stageRecall}</span>
          <span className={`px-3 py-1 rounded-full ${(stage === "quiz" || stage === "done") ? "bg-accent text-white accent-fg" : "bg-surface-2 text-secondary"}`}>3. {t.stageQuiz}</span>
        </div>
      )}
      {subject && topic && !streaming && (stage === "explained" || stage === "recalled") && (
        <div className="mt-3">
          {stage === "explained" && (
            <button data-testid="step-recall-btn" onClick={startRecall}
              className="w-full h-14 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-heading font-bold text-xl flex items-center justify-center gap-3 hover:opacity-90 transition-opacity">
              <PencilLine size={24} /> {t.stepRecall}
            </button>
          )}
          {stage === "recalled" && (
            <button data-testid="step-quiz-btn" onClick={startQuiz}
              className="w-full h-14 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-heading font-bold text-xl flex items-center justify-center gap-3 hover:opacity-90 transition-opacity">
              <ListChecks size={24} /> {t.stepQuiz}
            </button>
          )}
        </div>
      )}

      {subject && topic && !streaming && stage === "quiz" && (
        <button data-testid="lesson-complete-btn" onClick={completeLesson} disabled={completing}
          className="mt-3 w-full h-14 rounded-2xl bg-surface border-solid-2 font-heading font-bold text-xl flex items-center justify-center gap-3 hover:bg-surface-2 transition-colors disabled:opacity-50">
          {completing ? <Loader2 size={24} className="animate-spin" /> : <CheckCircle2 size={24} />} Dərsi bitir
        </button>
      )}
      {subject && topic && stage === "done" && !quiz && (
        <button data-testid="mini-quiz-btn" onClick={startMiniQuiz} disabled={quizLoading || streaming}
          className="mt-3 w-full h-14 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-heading font-bold text-xl flex items-center justify-center gap-3 hover:opacity-90 transition-opacity disabled:opacity-50">
          {quizLoading ? <><Loader2 size={24} className="animate-spin" /> Suallar hazırlanır...</> : "📝 Mini Quiz"}
        </button>
      )}
      {quiz && (
        <div className="mt-3 max-h-[60vh] overflow-y-auto">
          <QuizCard quiz={quiz} subject={subject} topic={topic}
            onSpeak={(txt) => speak(txt, "quiz-feedback")} onClose={() => { stop(); setQuiz(null); }} />
        </div>
      )}
      {!quiz && (
        <button data-testid="review-open-btn" onClick={() => setReviewOpen((v) => !v)} aria-expanded={reviewOpen}
          aria-label={t.reviewOpen}
          className="mt-3 w-full h-14 rounded-2xl bg-surface border-solid-2 font-heading font-bold text-xl flex items-center justify-center gap-3 hover:bg-surface-2 transition-colors focus:outline-none focus:ring-4">
          🔁 {reviewOpen ? t.reviewClose : t.reviewOpen}
        </button>
      )}
      {reviewOpen && !quiz && (
        <ReviewQuestions t={t} studentId={studentId} onSpeak={(txt) => speak(txt, "review")}
          onClose={() => { stop(); setReviewOpen(false); }} />
      )}
      {celebrate && (
        <div data-testid="lesson-celebrate" className="fixed inset-0 z-40 pointer-events-none flex items-center justify-center">
          {celebrate.confetti && <Confetti />}
          <div className="bg-surface border-solid-2 rounded-3xl px-8 py-6 text-center quiz-pop">
            <p className="font-heading font-bold text-3xl">Dərs bitdi! 🎉</p>
            <p className="text-2xl font-bold mt-2">+{celebrate.xp_earned} XP</p>
            {celebrate.badge_earned && <p className="text-xl mt-1">🏅 {celebrate.badge_earned}</p>}
          </div>
        </div>
      )}
      {readingText && (
        <ReadingMode text={readingText} lang={lang} speed={speed} onClose={() => setReadingText(null)} />
      )}

      {/* Quick asks */}
      <div className="flex flex-wrap gap-2 my-3">
        {quicks.map((q, i) => (
          <button key={q} data-testid={`quick-ask-${i}`} disabled={streaming} onClick={() => send(q)}
            className="inline-flex items-center gap-2 h-11 px-4 rounded-full bg-surface border-solid-2 font-semibold text-base hover:bg-surface-2 transition-colors disabled:opacity-50">
            <Sparkles size={18} className="text-accent" /> {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex items-end gap-3">
        <button data-testid="mic-btn" type="button" aria-label={t.micLabel} aria-pressed={listening}
          onPointerDown={startMic}
          onPointerUp={stopMic}
          onPointerCancel={stopMic}
          onLostPointerCapture={stopMic}
          onKeyDown={(e) => {
            if ((e.key === " " || e.key === "Enter") && !e.repeat) {
              e.preventDefault();
              startMic();
            }
          }}
          onKeyUp={(e) => {
            if (e.key === " " || e.key === "Enter") stopMic();
          }}
          onBlur={stopMic}
          className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 border-solid-2 transition-colors ${listening ? "bg-accent-warm pulse-ring" : "bg-surface hover:bg-surface-2"}`}
          style={{ ...(listening ? { background: "var(--accent-warm)", color: "#fff" } : {}), touchAction: "none" }}>
          {listening ? <Waveform /> : <Mic size={30} />}
        </button>
        <div className="flex-1 flex items-end gap-2 bg-surface border-solid-2 rounded-3xl p-2">
          <textarea ref={inputRef} data-testid="chat-input" value={input} rows={1} aria-label={t.chatInputLabel}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={listening ? t.listening : (stage === "recall_input" ? t.recallHint : stage === "quiz" ? t.quizHint : t.askPlaceholder)}
            className="flex-1 bg-transparent outline-none resize-none text-xl px-3 py-3 max-h-40" />
          <button data-testid="send-btn" onClick={() => send()} disabled={streaming || !input.trim()} aria-label={t.sendLabel}
            className="w-14 h-14 rounded-2xl bg-accent flex items-center justify-center shrink-0 disabled:opacity-40 hover:opacity-90 transition-opacity" style={{ color: "#fff" }}>
            {streaming ? <Loader2 size={26} className="animate-spin accent-fg" /> : <Send size={26} className="accent-fg" />}
          </button>
        </div>
      </div>
    </div>
  );
};
