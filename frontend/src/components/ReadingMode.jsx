import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, X, Volume2, Square, Loader2 } from "lucide-react";
import { useTTS } from "../hooks/useTTS";

// Markdown işarələrini silir və mətni cümlələrə bölür ([.!?…؟]); onluq kəsrdəki nöqtə (0.5) bölmür.
export const splitIntoSentences = (text) =>
  String(text || "")
    .replace(/\*\*|__|`+/g, "")
    .split(/\n+/)
    .map((line) => line.replace(/^\s*(?:[-*+•]\s+|#{1,6}\s+)/, ""))
    .flatMap((line) => line.match(/(?:[^.!?…؟]|\.(?=\d))+(?:[.!?…؟]+|$)/g) || [])
    .map((s) => s.trim())
    .filter((s) => /\p{L}/u.test(s));

/** Props: { text, lang, speed, onClose } — yüksək kontrastlı, cümlə-cümlə oxuma rejimi. */
export const ReadingMode = ({ text, lang, speed, onClose }) => {
  const sentences = useMemo(() => splitIntoSentences(text), [text]);
  const [index, setIndex] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);
  const { speak, stop, speakingId, loading } = useTTS(lang, speed);
  const current = sentences[index] || "";
  const speakId = `reading-${index}`;

  useEffect(() => {
    if (autoPlay && current) speak(current, speakId);
    // eslint-disable-next-line
  }, [index, autoPlay, current]);

  useEffect(() => () => stop(), [stop]);

  const go = (delta) => setIndex((i) => Math.min(sentences.length - 1, Math.max(0, i + delta)));
  const close = () => { stop(); onClose?.(); };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line
  }, [sentences.length]);

  const speaking = speakingId === speakId;

  return (
    <div data-testid="reading-mode" role="dialog" aria-modal="true" aria-label="Oxuma rejimi"
      className="fixed inset-0 z-50 flex flex-col"
      style={{ background: "#000000", color: "#FFFF00" }}>
      <div className="flex items-center justify-between gap-3 p-4">
        <span data-testid="reading-counter" className="font-bold" style={{ fontSize: 28 }}>
          {sentences.length ? `${index + 1} / ${sentences.length}` : "0 / 0"}
        </span>
        <div className="flex gap-3">
          <button data-testid="reading-play-btn"
            onClick={() => { if (speaking) { stop(); setAutoPlay(false); } else { setAutoPlay(true); speak(current, speakId); } }}
            aria-label={speaking ? "Dayandır" : "Dinlə"}
            className="h-16 px-5 rounded-2xl font-bold inline-flex items-center gap-2"
            style={{ border: "3px solid #FFFF00", fontSize: 24 }}>
            {speaking ? (loading ? <Loader2 size={30} className="animate-spin" /> : <Square size={28} />) : <Volume2 size={30} />}
            {speaking ? "Dayandır" : "Dinlə"}
          </button>
          <button data-testid="reading-close-btn" onClick={close}
            className="h-16 px-5 rounded-2xl font-bold inline-flex items-center gap-2"
            style={{ background: "#FFFF00", color: "#000000", fontSize: 24 }}>
            <X size={30} /> Bağla
          </button>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-6 overflow-y-auto">
        <p data-testid="reading-sentence" aria-live="polite" className="font-heading font-bold text-center leading-snug max-w-5xl"
          style={{ fontSize: "clamp(36px, 6vw, 64px)" }}>
          {current || "Oxunacaq mətn yoxdur."}
        </p>
      </div>

      <div className="flex items-center justify-between gap-4 p-4">
        <button data-testid="reading-prev-btn" onClick={() => go(-1)} disabled={index === 0} aria-label="Əvvəlki cümlə"
          className="w-28 h-24 rounded-3xl flex items-center justify-center disabled:opacity-30"
          style={{ border: "4px solid #FFFF00" }}>
          <ChevronLeft size={64} />
        </button>
        <button data-testid="reading-next-btn" onClick={() => go(1)} disabled={index >= sentences.length - 1} aria-label="Növbəti cümlə"
          className="w-28 h-24 rounded-3xl flex items-center justify-center disabled:opacity-30"
          style={{ background: "#FFFF00", color: "#000000" }}>
          <ChevronRight size={64} />
        </button>
      </div>
    </div>
  );
};

export default ReadingMode;
