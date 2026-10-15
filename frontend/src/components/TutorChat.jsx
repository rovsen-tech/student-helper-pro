import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowLeft, Send, Mic, Volume2, Square, Loader2, GraduationCap, Sparkles, PencilLine, ListChecks, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useTTS } from "../hooks/useTTS";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Waveform = () => (
  <div className="flex items-end gap-1 h-6">
    {[0, 1, 2, 3, 4].map((i) => (
      <span key={i} className="wave-bar w-1.5 bg-white rounded-full accent-fg"
        style={{ background: "currentColor", animationDelay: `${i * 0.12}s`, height: "40%" }} />
    ))}
  </div>
);

export const TutorChat = ({ t, lang, ctx, speed, voice, onBack }) => {
  const book = ctx.kind === "book" ? ctx.book : null;
  const subject = ctx.kind === "lesson" ? ctx.subject : null;
  const topic = ctx.kind === "lesson" ? ctx.topic : null;
  const lessonId = ctx.kind === "lesson" ? ctx.lessonId : null;
  const sid = ctx.sid;
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [listening, setListening] = useState(false);
  const [stage, setStage] = useState(null);
  const [retryAction, setRetryAction] = useState(null);
  const { speak, stop, speakingId, loading } = useTTS(lang, speed, voice);
  const scrollRef = useRef(null);
  const recRef = useRef(null);
  const inputRef = useRef(null);
  const autoSpokeRef = useRef(false);

  const scrollDown = () => setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 50);

  const qs = () => {
    const p = new URLSearchParams();
    if (sid) p.set("student_id", sid);
    if (book) p.set("book_id", book.id);
    if (subject) { p.set("subject", subject); p.set("topic", topic); }
    return p.toString();
  };

  const readStream = async (res, aiId) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "", full = "", error = false;
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
          } else if (obj.error) {
            error = true;
          }
        } catch (err) { console.warn("SSE parse skipped", err); }
      }
    }
    return { full, error };
  };

  const runAssistant = async (body, seedId, retryFn) => {
    const aiId = seedId || `a${Date.now()}`;
    setMessages((m) => (seedId ? [{ role: "assistant", content: "", id: aiId }] : [...m, { role: "assistant", content: "", id: aiId }]));
    setStreaming(true);
    setRetryAction(null);
    scrollDown();
    let result = { full: "", error: false };
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("http " + res.status);
      result = await readStream(res, aiId);
    } catch (err) {
      console.error("assistant error", err);
      result.error = true;
    } finally { setStreaming(false); scrollDown(); }
    if (result.error || !result.full.trim()) {
      setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, content: "", error: true } : x)));
      setRetryAction(() => (retryFn || (() => runAssistant(body, seedId, retryFn))));
      return false;
    }
    speak(result.full, aiId);
    return true;
  };

  const streamExplain = async () => {
    const ok = await runAssistant({ subject, topic, lang, explain: true, lesson_id: lessonId, student_id: sid }, "explain", streamExplain);
    if (ok) setStage("explained");
  };

  const startRecall = () => { setStage("recall_input"); inputRef.current?.focus(); };

  const startQuiz = async () => {
    setStage("quiz");
    await runAssistant({ subject, topic, lang, stage: "quiz_next", lesson_id: lessonId, student_id: sid }, undefined, startQuiz);
  };

  const initRef = useRef(null);
  useEffect(() => {
    const key = `${book?.id || ""}|${subject || ""}|${topic || ""}`;
    if (initRef.current === key) return;
    initRef.current = key;
    const load = async () => {
      let hist = [];
      try {
        const res = await fetch(`${API}/messages?${qs()}`);
        hist = await res.json();
      } catch (err) { console.error("Failed to load messages", err); }
      if (hist.length > 0) {
        setMessages(hist);
        if (subject && topic) setStage("explained");
        scrollDown();
        return;
      }
      if (subject && topic) { streamExplain(); return; }
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
    setRetryAction(null);
    const effStage = subject && topic
      ? (stage === "recall_input" ? "recall" : stage === "quiz" ? "quiz_answer" : undefined)
      : undefined;
    const userMsg = { role: "user", content: msg, id: `u${Date.now()}` };
    const aiId = `a${Date.now()}`;
    setMessages((m) => [...m, userMsg, { role: "assistant", content: "", id: aiId }]);
    setStreaming(true);
    scrollDown();
    const body = { book_id: book?.id || null, subject, topic, message: msg, lang, stage: effStage, lesson_id: lessonId, student_id: sid };
    let result = { full: "", error: false };
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("http " + res.status);
      result = await readStream(res, aiId);
    } catch (err) {
      console.error("send error", err);
      result.error = true;
    } finally {
      setStreaming(false);
      scrollDown();
    }
    if (result.error || !result.full.trim()) {
      setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, content: "", error: true } : x)));
      setRetryAction(() => () => send(msg));
      return;
    }
    speak(result.full, aiId);
    if (effStage === "recall") setStage("recalled");
  }, [input, streaming, book, subject, topic, lang, stage, speak, stop]);

  const startMic = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast.error(t.micError); return; }
    stop();
    const rec = new SR();
    rec.lang = lang === "az" ? "az-AZ" : "tr-TR";
    rec.interimResults = false;
    rec.onresult = (e) => { const txt = e.results[0][0].transcript; setInput(txt); send(txt); };
    rec.onerror = () => { setListening(false); toast.error(t.micError); };
    rec.onend = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    rec.start();
  };
  const stopMic = () => { recRef.current?.stop(); setListening(false); };

  const quicks = [t.q1, t.q2, t.q3];

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col" style={{ height: "calc(100vh - 76px)" }}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <button data-testid="chat-back-btn" onClick={onBack}
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
      </div>

      {/* Messages */}
      <div ref={scrollRef} data-testid="chat-messages" className="flex-1 overflow-y-auto space-y-4 pr-1 pb-2">
        {messages.map((m) => (
          <div key={m.id} className={`rise flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-3xl px-5 py-4 border-solid-2 ${m.role === "user" ? "bg-accent text-white accent-fg" : "bg-surface"}`}
              style={m.role === "user" ? { borderColor: "var(--accent)" } : {}}>
              {m.error ? (
                <div data-testid="error-block">
                  <p className="text-xl leading-relaxed">{t.errorMsg}</p>
                  <button data-testid="retry-btn" onClick={() => { const fn = retryAction; setRetryAction(null); if (fn) fn(); }}
                    className="mt-3 inline-flex items-center gap-2 h-11 px-4 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-bold text-lg hover:opacity-90 transition-opacity">
                    <RefreshCw size={22} /> {t.retryBtn}
                  </button>
                </div>
              ) : (
                <>
                  <p className="text-xl whitespace-pre-wrap leading-relaxed">{m.content || (streaming ? t.thinking : "")}</p>
                  {m.role === "assistant" && m.content && (
                    <button data-testid={`listen-btn-${m.id}`} onClick={() => (speakingId === m.id ? stop() : speak(m.content, m.id))}
                      className="mt-3 inline-flex items-center gap-2 h-11 px-4 rounded-2xl bg-surface-2 border-solid-2 font-bold text-lg hover:bg-accent hover:text-white transition-colors">
                      {speakingId === m.id ? (loading ? <Loader2 size={22} className="animate-spin" /> : <Square size={20} />) : <Volume2 size={22} />}
                      {speakingId === m.id ? t.stop : t.listen}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Stage controls (lessons only) */}
      {subject && topic && stage && (
        <div data-testid="stage-indicator" className="flex flex-wrap items-center gap-2 text-base font-semibold mt-3">
          <span className={`px-3 py-1 rounded-full ${stage === "explained" ? "bg-accent text-white accent-fg" : "bg-surface-2 text-secondary"}`}>1. {t.stageExplain}</span>
          <span className={`px-3 py-1 rounded-full ${(stage === "recall_input" || stage === "recalled") ? "bg-accent text-white accent-fg" : "bg-surface-2 text-secondary"}`}>2. {t.stageRecall}</span>
          <span className={`px-3 py-1 rounded-full ${stage === "quiz" ? "bg-accent text-white accent-fg" : "bg-surface-2 text-secondary"}`}>3. {t.stageQuiz}</span>
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
        <button data-testid="mic-btn" onClick={listening ? stopMic : startMic}
          className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 border-solid-2 transition-colors ${listening ? "bg-accent-warm pulse-ring" : "bg-surface hover:bg-surface-2"}`}
          style={listening ? { background: "var(--accent-warm)", color: "#fff" } : {}}>
          {listening ? <Waveform /> : <Mic size={30} />}
        </button>
        <div className="flex-1 flex items-end gap-2 bg-surface border-solid-2 rounded-3xl p-2">
          <textarea ref={inputRef} data-testid="chat-input" value={input} rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={listening ? t.listening : (stage === "recall_input" ? t.recallHint : stage === "quiz" ? t.quizHint : t.askPlaceholder)}
            className="flex-1 bg-transparent outline-none resize-none text-xl px-3 py-3 max-h-40" />
          <button data-testid="send-btn" onClick={() => send()} disabled={streaming || !input.trim()}
            className="w-14 h-14 rounded-2xl bg-accent flex items-center justify-center shrink-0 disabled:opacity-40 hover:opacity-90 transition-opacity" style={{ color: "#fff" }}>
            {streaming ? <Loader2 size={26} className="animate-spin accent-fg" /> : <Send size={26} className="accent-fg" />}
          </button>
        </div>
      </div>
    </div>
  );
};
