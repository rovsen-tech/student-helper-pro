import { useState } from "react";
import { Loader2, X, Lightbulb, ArrowRight } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const QUIZ_CSS = `
@keyframes quiz-pop { 0% { transform: scale(.85); opacity: 0 } 60% { transform: scale(1.04); opacity: 1 } 100% { transform: scale(1) } }
@keyframes quiz-shake { 0%,100% { transform: translateX(0) } 25% { transform: translateX(-8px) } 75% { transform: translateX(8px) } }
@keyframes quiz-confetti { 0% { transform: translateY(-20px) rotate(0); opacity: 1 } 100% { transform: translateY(420px) rotate(720deg); opacity: 0 } }
.quiz-pop { animation: quiz-pop .35s ease-out both }
.quiz-shake { animation: quiz-shake .35s ease-in-out }
.quiz-confetti-piece { position: absolute; top: 0; width: 12px; height: 18px; border-radius: 3px; animation: quiz-confetti 2.4s ease-in forwards }
@media (prefers-reduced-motion: reduce) { .quiz-pop, .quiz-shake, .quiz-confetti-piece { animation: none } }
`;

const CONFETTI_COLORS = ["#F59E0B", "#10B981", "#3B82F6", "#EF4444", "#A855F7", "#EC4899"];

export const Confetti = () => (
  <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
    {Array.from({ length: 36 }).map((_, i) => (
      <span key={i} className="quiz-confetti-piece"
        style={{ left: `${(i * 37) % 100}%`, background: CONFETTI_COLORS[i % CONFETTI_COLORS.length], animationDelay: `${(i % 9) * 0.12}s` }} />
    ))}
  </div>
);

/**
 * Props: { quiz: {quiz_id, questions}, subject, topic, onClose, onSpeak? }
 */
export const QuizCard = ({ quiz, subject, topic, onClose, onSpeak }) => {
  const questions = quiz?.questions ?? [];
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);
  const [xpTotal, setXpTotal] = useState(0);
  const [badge, setBadge] = useState(null);
  const [finished, setFinished] = useState(false);

  const q = questions[index];

  const submit = async (value) => {
    const studentAnswer = String(value ?? answer).trim();
    if (!studentAnswer || submitting || result) return;
    setSelected(studentAnswer);
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/quiz/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quiz_id: quiz.quiz_id, question_id: q.id, student_answer: studentAnswer, subject, topic }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
      if (data.correct) setCorrectCount((c) => c + 1);
      setXpTotal((x) => x + (data.xp_earned || 0));
      if (data.badge_earned) setBadge(data.badge_earned);
      onSpeak?.([data.correct ? "Düzdür!" : "", data.feedback, data.encouragement].filter(Boolean).join(" "));
    } catch (err) {
      console.error("Quiz submit failed", err);
      setResult({ error: true, feedback: "Bağlantı xətası. Yenidən cəhd et." });
      setSelected(null);
    } finally { setSubmitting(false); }
  };

  const next = () => {
    if (result?.error) { setResult(null); return; }
    if (index + 1 >= questions.length) { setFinished(true); return; }
    setIndex((i) => i + 1);
    setAnswer(""); setSelected(null); setResult(null); setShowHint(false);
  };

  if (!questions.length) return null;

  if (finished) {
    const perfect = correctCount === questions.length;
    return (
      <div data-testid="quiz-complete" className="relative bg-surface border-solid-2 rounded-3xl p-6 text-center quiz-pop overflow-hidden">
        <style>{QUIZ_CSS}</style>
        <Confetti />
        <p className="text-6xl mb-3">{perfect ? "🏆" : "🎉"}</p>
        <h3 className="font-heading font-bold text-4xl mb-3">Əla iş! 🎉</h3>
        <p className="text-2xl font-semibold mb-2" data-testid="quiz-score">{correctCount} / {questions.length} düzgün cavab</p>
        <p className="text-2xl font-bold text-accent mb-2" data-testid="quiz-xp">+{xpTotal} XP</p>
        {perfect && <p className="text-xl mb-2">Hamısı düzdür! Bonus XP qazandın! ⭐</p>}
        {badge && <p className="text-xl font-bold mb-2">🏅 Yeni nişan: {badge}</p>}
        <button data-testid="quiz-close-btn" onClick={onClose}
          className="mt-4 h-14 px-8 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-heading font-bold text-xl hover:opacity-90">
          Bağla
        </button>
      </div>
    );
  }

  const isMC = q.type === "multiple_choice" && Array.isArray(q.options);
  const optionClass = (opt) => {
    if (!result || result.error) return "bg-surface-2 hover:bg-accent hover:text-white";
    if (opt === result.correct_answer) return "bg-green-600 text-white";
    if (opt === selected) return "bg-red-600 text-white quiz-shake";
    return "bg-surface-2 opacity-60";
  };

  return (
    <div data-testid="quiz-card" className="bg-surface border-solid-2 rounded-3xl p-5 quiz-pop" key={q.id}>
      <style>{QUIZ_CSS}</style>
      <div className="flex items-center justify-between mb-4 gap-3">
        <span className="text-lg font-bold text-secondary" data-testid="quiz-counter">Sual {index + 1} / {questions.length}</span>
        <button data-testid="quiz-exit-btn" onClick={onClose} aria-label="Bağla"
          className="w-12 h-12 rounded-2xl bg-surface-2 border-solid-2 flex items-center justify-center"><X size={24} /></button>
      </div>
      <h3 className="font-heading font-bold text-3xl leading-snug mb-5" data-testid="quiz-question">{q.question}</h3>

      {isMC ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {q.options.map((opt, i) => (
            <button key={opt} data-testid={`quiz-option-${i}`} disabled={!!result && !result.error || submitting}
              onClick={() => submit(opt)}
              className={`min-h-16 px-5 py-4 rounded-2xl border-solid-2 text-2xl font-bold text-left transition-colors ${optionClass(opt)}`}>
              <span className="mr-2">{String.fromCharCode(65 + i)})</span>{opt}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex gap-3">
          <input data-testid="quiz-answer-input" value={answer} disabled={!!result && !result.error}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            placeholder="Cavabını yaz..."
            className="flex-1 h-16 px-4 rounded-2xl bg-surface-2 border-solid-2 text-2xl outline-none" />
          <button data-testid="quiz-submit-btn" onClick={() => submit()} disabled={submitting || !answer.trim() || (!!result && !result.error)}
            className="h-16 px-6 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-bold text-xl disabled:opacity-40">
            Yoxla
          </button>
        </div>
      )}

      {submitting && <p className="mt-4 flex items-center gap-2 text-xl"><Loader2 className="animate-spin" size={24} /> Yoxlanılır...</p>}

      {!result && !submitting && q.hint && (
        showHint
          ? <p className="mt-4 text-xl flex gap-2" data-testid="quiz-hint"><Lightbulb size={26} className="shrink-0" /> {q.hint}</p>
          : <button data-testid="quiz-hint-btn" onClick={() => setShowHint(true)}
              className="mt-4 h-12 px-4 rounded-2xl bg-surface-2 border-solid-2 font-bold text-lg inline-flex items-center gap-2">
              <Lightbulb size={22} /> İpucu
            </button>
      )}

      {result && (
        <div data-testid="quiz-feedback" role="status"
          className={`mt-5 rounded-2xl p-4 border-solid-2 quiz-pop ${result.error ? "" : result.correct ? "bg-green-100 text-green-900" : "bg-red-100 text-red-900"}`}>
          {!result.error && <p className="text-3xl font-bold mb-1">{result.correct ? "✅ Düzdür!" : "❌ Bu dəfə alınmadı"}</p>}
          {result.feedback && <p className="text-xl">{result.feedback}</p>}
          {!result.error && !result.correct && result.hint && <p className="text-xl mt-1">💡 {result.hint}</p>}
          {result.encouragement && <p className="text-xl font-semibold mt-1">{result.encouragement}</p>}
          {result.xp_earned > 0 && <p className="text-xl font-bold mt-1">+{result.xp_earned} XP</p>}
          <button data-testid="quiz-next-btn" onClick={next}
            className="mt-3 h-14 px-6 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-bold text-xl inline-flex items-center gap-2">
            {result.error ? "Yenidən cəhd et" : index + 1 >= questions.length ? "Nəticəni gör" : "Növbəti sual"} <ArrowRight size={22} />
          </button>
        </div>
      )}
    </div>
  );
};

export default QuizCard;
