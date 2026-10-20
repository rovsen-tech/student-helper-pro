import { useEffect, useState } from "react";
import { Loader2, RotateCcw, Volume2, X } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/** "Təkrar sualları": zəif mövzular üzrə ən çox 5 sual (LLM yoxdur). Props: { t, studentId, onSpeak, onClose } */
export const ReviewQuestions = ({ t, studentId, onSpeak, onClose }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [shown, setShown] = useState({});
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError(false);
    setShown({});
    fetch(`${API}/progress/review-questions`) // X-Student-Id qlobal interceptor ilə əlavə olunur
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => alive && setData(d))
      .catch((err) => { console.error("Review questions failed", err); if (alive) setError(true); });
    return () => { alive = false; };
  }, [studentId, reload]);

  const items = data?.items ?? [];
  const btn = "min-h-12 px-4 rounded-2xl border-solid-2 font-bold text-lg flex items-center gap-2 focus:outline-none focus:ring-4";

  return (
    <section data-testid="review-questions" aria-labelledby="review-title"
      className="mt-3 rounded-3xl bg-surface border-solid-2 p-5 max-h-[60vh] overflow-y-auto">
      <div className="flex items-center gap-3 mb-4">
        <RotateCcw size={28} className="text-accent shrink-0" aria-hidden="true" />
        <h2 id="review-title" className="font-heading font-extrabold text-2xl flex-1">{t.reviewTitle}</h2>
        <button data-testid="review-close-btn" onClick={onClose} aria-label={t.reviewClose}
          className={`${btn} bg-surface-2`}><X size={24} aria-hidden="true" /></button>
      </div>

      {error ? (
        <div role="alert" data-testid="review-error" className="p-4 rounded-2xl bg-red-100 text-red-900 border-solid-2 text-xl font-bold">
          <p>{t.reviewLoadError}</p>
          <button onClick={() => setReload((n) => n + 1)} className={`${btn} mt-3 bg-white`}>{t.reviewRetry}</button>
        </div>
      ) : !data ? (
        <div className="flex justify-center py-6" role="status" aria-label={t.loading}>
          <Loader2 size={36} className="animate-spin text-accent" />
        </div>
      ) : items.length === 0 ? (
        <p data-testid="review-empty" className="text-xl">{t.noReview}</p>
      ) : (
        <ol className="space-y-4" aria-live="polite">
          {items.map((it, i) => (
            <li key={`${it.topic}-${i}`} data-testid={`review-item-${i}`} className="p-4 rounded-2xl bg-surface-2 border-solid-2">
              <p className="text-base font-semibold text-secondary">
                {it.subject} · {it.topic} · {it.source === "mistake" ? t.reviewFromMistake : t.reviewFromCurriculum}
              </p>
              <p className="text-2xl font-bold mt-1">{i + 1}. {it.question}</p>
              <div className="flex flex-wrap gap-2 mt-3">
                <button onClick={() => onSpeak?.(it.question)} aria-label={`${t.reviewListen}: ${it.question}`}
                  className={`${btn} bg-surface`}><Volume2 size={22} aria-hidden="true" /> {t.reviewListen}</button>
                {it.answer && (
                  <button onClick={() => setShown((s) => ({ ...s, [i]: !s[i] }))} aria-expanded={!!shown[i]}
                    aria-controls={`review-answer-${i}`} className={`${btn} bg-accent text-white accent-fg`}>
                    {shown[i] ? t.reviewHideAnswer : t.reviewShowAnswer}
                  </button>
                )}
              </div>
              {it.answer && shown[i] && (
                <p id={`review-answer-${i}`} className="mt-3 text-2xl font-extrabold">{t.reviewAnswer}: {it.answer}</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
};

export default ReviewQuestions;
