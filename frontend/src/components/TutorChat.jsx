import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowLeft, Send, Mic, Volume2, Square, Loader2, GraduationCap, Sparkles } from "lucide-react";
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

export const TutorChat = ({ t, lang, book, speed, onBack }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [listening, setListening] = useState(false);
  const { speak, stop, speakingId, loading } = useTTS(lang, speed);
  const scrollRef = useRef(null);
  const recRef = useRef(null);
  const autoSpokeRef = useRef(false);

  const scrollDown = () => setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 50);

  useEffect(() => {
    const load = async () => {
      const seed = [];
      if (book) {
        const intro = `${book.explanation}`;
        seed.push({ role: "assistant", content: intro, id: "intro" });
      } else {
        seed.push({ role: "assistant", content: t.welcome, id: "intro" });
      }
      try {
        const res = await fetch(`${API}/messages/${book?.id || "general"}`);
        const hist = await res.json();
        setMessages([...seed, ...hist]);
      } catch {
        setMessages(seed);
      }
      scrollDown();
    };
    load();
    // eslint-disable-next-line
  }, [book?.id]);

  const send = useCallback(async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || streaming) return;
    stop();
    setInput("");
    const userMsg = { role: "user", content: msg, id: `u${Date.now()}` };
    const aiId = `a${Date.now()}`;
    setMessages((m) => [...m, userMsg, { role: "assistant", content: "", id: aiId }]);
    setStreaming(true);
    scrollDown();
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: book?.id || null, message: msg, lang }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let full = "";
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
          } catch {}
        }
      }
      if (full) speak(full, aiId);
    } catch {
      toast.error("Xəta");
    } finally {
      setStreaming(false);
      scrollDown();
    }
  }, [input, streaming, book, lang, speak, stop]);

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
          <h2 className="font-heading font-bold text-2xl truncate">{book ? book.title : t.general}</h2>
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
              <p className="text-xl whitespace-pre-wrap leading-relaxed">{m.content || (streaming ? t.thinking : "")}</p>
              {m.role === "assistant" && m.content && (
                <button data-testid={`listen-btn-${m.id}`} onClick={() => (speakingId === m.id ? stop() : speak(m.content, m.id))}
                  className="mt-3 inline-flex items-center gap-2 h-11 px-4 rounded-2xl bg-surface-2 border-solid-2 font-bold text-lg hover:bg-accent hover:text-white transition-colors">
                  {speakingId === m.id ? (loading ? <Loader2 size={22} className="animate-spin" /> : <Square size={20} />) : <Volume2 size={22} />}
                  {speakingId === m.id ? t.stop : t.listen}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Quick asks */}
      <div className="flex flex-wrap gap-2 my-3">
        {quicks.map((q, i) => (
          <button key={i} data-testid={`quick-ask-${i}`} disabled={streaming} onClick={() => send(q)}
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
          <textarea data-testid="chat-input" value={input} rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={listening ? t.listening : t.askPlaceholder}
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
