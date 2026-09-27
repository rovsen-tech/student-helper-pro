import { useEffect, useState } from "react";
import * as Icons from "lucide-react";
import { ArrowLeft, BarChart3, MessageCircleQuestion, BookOpen, CheckCircle2, Clock, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Stat = ({ icon: Icon, label, value, testid }) => (
  <div data-testid={testid} className="p-6 rounded-3xl bg-surface border-solid-2 flex items-center gap-4">
    <div className="w-14 h-14 rounded-2xl bg-surface-2 flex items-center justify-center shrink-0 text-accent"><Icon size={28} /></div>
    <div>
      <div className="font-heading font-extrabold text-4xl">{value ?? 0}</div>
      <div className="text-secondary text-base">{label}</div>
    </div>
  </div>
);

export const ParentPanel = ({ t, subjects, onBack }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const meta = (name) => subjects.find((s) => s.name === name) || {};

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/progress`);
        setData(await r.json());
      } catch (err) {
        console.error("Failed to load progress", err);
        setData({ total_questions: 0, subjects_studied: 0, lessons_started: 0, by_subject: [] });
      } finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-8">
        <button data-testid="parent-back-btn" onClick={onBack}
          className="w-12 h-12 rounded-2xl bg-surface border-solid-2 flex items-center justify-center hover:bg-surface-2 transition-colors shrink-0">
          <ArrowLeft size={26} />
        </button>
        <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center shrink-0" style={{ color: "#fff" }}>
          <BarChart3 size={32} className="accent-fg" />
        </div>
        <div className="min-w-0">
          <h1 className="font-heading font-extrabold text-3xl sm:text-4xl leading-tight">{t.parentTitle}</h1>
          <p className="text-secondary text-lg">{t.parentDesc}</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 size={40} className="animate-spin text-accent" /></div>
      ) : (
        <>
          <div className="grid sm:grid-cols-3 gap-4 mb-10">
            <Stat icon={MessageCircleQuestion} label={t.totalQuestions} value={data.total_questions} testid="stat-questions" />
            <Stat icon={BookOpen} label={t.subjectsStudied} value={data.subjects_studied} testid="stat-subjects" />
            <Stat icon={Clock} label={t.lessonsStarted} value={data.lessons_started} testid="stat-lessons" />
          </div>

          {data.by_subject.length === 0 ? (
            <div data-testid="parent-empty" className="p-10 rounded-3xl bg-surface border-solid-2 text-center text-secondary text-xl">{t.noActivity}</div>
          ) : (
            <div className="space-y-5">
              {data.by_subject.map((s, i) => {
                const m = meta(s.subject);
                const Icon = Icons[m.icon] || BookOpen;
                const color = m.color || "var(--accent)";
                return (
                  <div key={s.subject} data-testid={`parent-subject-${i}`} className="rise rounded-3xl bg-surface border-solid-2 overflow-hidden" style={{ animationDelay: `${i * 50}ms` }}>
                    <div className="flex items-center gap-4 p-5 bg-surface-2">
                      <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0" style={{ background: color, color: "#fff" }}><Icon size={28} /></div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-heading font-bold text-2xl truncate">{s.subject}</h3>
                        <p className="text-secondary text-base">{s.total_questions} {t.questionsLabel}</p>
                      </div>
                    </div>
                    <div>
                      {s.lessons.map((l) => (
                        <div key={l.topic} className="flex items-center gap-3 px-5 py-4 border-t" style={{ borderColor: "var(--border)" }}>
                          <span className="font-heading font-bold text-lg flex-1 min-w-0 truncate">{l.topic}</span>
                          {l.explained && (
                            <span className="inline-flex items-center gap-1 text-base font-semibold text-accent shrink-0"><CheckCircle2 size={18} /> {t.explainedBadge}</span>
                          )}
                          <span className="inline-flex items-center gap-1 text-base font-semibold text-secondary shrink-0"><MessageCircleQuestion size={18} /> {l.question_count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};
