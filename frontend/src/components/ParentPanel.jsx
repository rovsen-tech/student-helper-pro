import { useEffect, useState } from "react";
import { ArrowLeft, BarChart3, Trophy, Flame, Star, Target, AlertTriangle, HelpCircle, Loader2, Puzzle, XCircle, RotateCcw, ScrollText } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getJson = async (path) => {
  const r = await fetch(`${API}${path}`); // X-Student-Id qlobal interceptor ilə əlavə olunur
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
};

const Stat = ({ icon: Icon, label, value, testid }) => (
  <div data-testid={testid} className="p-5 rounded-3xl bg-surface border-solid-2 flex items-center gap-4">
    <div className="w-14 h-14 rounded-2xl bg-surface-2 flex items-center justify-center shrink-0 text-accent"><Icon size={28} aria-hidden="true" /></div>
    <div>
      <div className="font-heading font-extrabold text-3xl">{value ?? 0}</div>
      <div className="text-secondary text-base">{label}</div>
    </div>
  </div>
);

const Section = ({ title, icon: Icon, children, testid }) => (
  <section data-testid={testid} className="rounded-3xl bg-surface border-solid-2 p-5 mb-6" aria-label={title}>
    <h2 className="font-heading font-bold text-2xl mb-4 flex items-center gap-2"><Icon size={26} className="text-accent" aria-hidden="true" /> {title}</h2>
    {children}
  </section>
);

export const ParentPanel = ({ t, studentId, onBack }) => {
  const [stats, setStats] = useState(null);
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [gaps, setGaps] = useState(null);
  const [errors, setErrors] = useState(null);
  const [analysisFailed, setAnalysisFailed] = useState(false);
  const [reload, setReload] = useState(0);
  const [summaries, setSummaries] = useState([]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);
    setAnalysisFailed(false);
    Promise.allSettled([
      getJson("/progress/stats"), getJson("/progress/review-questions"),
      getJson("/progress/skill-gaps"), getJson("/progress/error-analysis"), getJson("/lesson-summaries"),
    ]).then(([s, r, g, e, ls]) => {
      if (!alive) return;
      setSummaries(ls.status === "fulfilled" ? ls.value : []);
      setGaps(g.status === "fulfilled" ? g.value.skill_gaps ?? [] : null);
      setErrors(e.status === "fulfilled" ? e.value.top_errors ?? [] : null);
      if (g.status === "rejected" || e.status === "rejected") {
        console.error("Analysis failed", g.reason || e.reason);
        setAnalysisFailed(true);
      }
      setStats(s.status === "fulfilled" ? s.value : null);
      setReview(r.status === "fulfilled" ? r.value : null);
      if (s.status === "rejected") { console.error("Stats failed", s.reason); setError(true); }
      if (r.status === "rejected") console.error("Review failed", r.reason);
      setLoading(false);
    });
    return () => { alive = false; };
  }, [studentId, reload]);

  const mastery = stats?.mastery ?? [];
  const badges = stats?.badges ?? [];
  const weak = review?.weak_topics ?? [];
  const items = review?.items ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-8">
        <button data-testid="parent-back-btn" onClick={onBack} aria-label={t.back}
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
        <div className="flex justify-center py-20"><Loader2 size={40} className="animate-spin text-accent" aria-label={t.loading} /></div>
      ) : error || !stats ? (
        <p role="alert" data-testid="parent-error" className="p-8 rounded-3xl bg-surface border-solid-2 text-center text-xl">{t.parentLoadError}</p>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Stat icon={Star} label={t.xpLabel} value={stats.total_xp} testid="stat-xp" />
            <Stat icon={Trophy} label={t.levelLabel} value={stats.level} testid="stat-level" />
            <Stat icon={Flame} label={t.streakLabel} value={stats.streak_days} testid="stat-streak" />
            <Stat icon={Target} label={t.topicsMasteredLabel} value={stats.topics_mastered} testid="stat-mastered" />
          </div>

          <Section title={t.summaryTitle} icon={ScrollText} testid="parent-summaries">
            {summaries.length ? (
              <ul className="space-y-3">
                {summaries.map((su) => (
                  <li key={su.id} data-testid={`summary-item-${su.id}`} className="p-4 rounded-2xl bg-surface-2 border-solid-2">
                    <p className="font-heading font-bold text-lg">{su.topic} <span className="text-secondary text-base font-semibold">· {su.subject} · {new Date(su.created_at).toLocaleDateString("ru-RU")}</span></p>
                    <p className="text-lg mt-1">{su.summary}</p>
                  </li>
                ))}
              </ul>
            ) : <p className="text-lg text-secondary" data-testid="summaries-empty">{t.noSummaries}</p>}
          </Section>

          <Section title={t.badgesTitle} icon={Trophy} testid="parent-badges">
            {badges.length ? (
              <div className="flex flex-wrap gap-2">
                {badges.map((b) => <span key={b} className="px-4 py-2 rounded-full bg-accent text-white accent-fg font-bold text-lg">🏅 {b}</span>)}
              </div>
            ) : <p className="text-lg text-secondary">{t.noBadges}</p>}
          </Section>

          <Section title={t.masteryTitle} icon={Target} testid="parent-mastery">
            {mastery.length ? (
              <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
                {mastery.map((m) => (
                  <li key={`${m.subject}|${m.topic}`} className="py-3 flex flex-wrap items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-heading font-bold text-lg truncate">{m.topic}</p>
                      <p className="text-secondary text-base">{m.subject}</p>
                    </div>
                    <span className="px-3 py-1 rounded-full bg-surface-2 border-solid-2 font-bold text-base">{m.level}</span>
                    <span className="font-bold text-lg w-24 text-right" aria-label={`${t.accuracyLabel}: ${m.recent_accuracy_pct ?? 0}%`}>
                      {m.recent_accuracy_pct ?? 0}%
                    </span>
                  </li>
                ))}
              </ul>
            ) : <p className="text-lg text-secondary">{t.noActivity}</p>}
          </Section>

          <Section title={t.weakTopicsTitle} icon={AlertTriangle} testid="parent-weak">
            {weak.length ? (
              <ul className="list-disc pl-6 space-y-1 text-lg">
                {weak.map((w) => <li key={`${w.subject}|${w.topic}`}><b>{w.topic}</b> — {w.subject} ({w.level})</li>)}
              </ul>
            ) : <p className="text-lg text-secondary">{t.noWeakTopics}</p>}
          </Section>

          {analysisFailed && (
            <div role="alert" data-testid="parent-analysis-error"
              className="mb-6 p-5 rounded-3xl bg-red-100 text-red-900 border-solid-2 text-xl font-bold flex flex-wrap items-center gap-3">
              <span className="flex-1">{t.analysisLoadError}</span>
              <button type="button" onClick={() => setReload((n) => n + 1)} aria-label={t.analysisRetry}
                className="min-h-12 px-4 rounded-2xl bg-white border-solid-2 flex items-center gap-2 focus:outline-none focus:ring-4">
                <RotateCcw size={22} aria-hidden="true" /> {t.analysisRetry}
              </button>
            </div>
          )}

          {gaps && (
            <Section title={t.skillGapsTitle} icon={Puzzle} testid="parent-skill-gaps">
              {gaps.length ? (
                <ul className="space-y-4">
                  {gaps.map((g) => (
                    <li key={`${g.subject}|${g.topic}`} className="p-4 rounded-2xl bg-surface-2 border-solid-2"
                      aria-label={`${g.topic}, ${g.subject}: ${t.accuracyLabel} ${g.accuracy_pct}%`}>
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-heading font-bold text-xl flex-1 min-w-0">{g.topic} <span className="text-secondary text-base font-semibold">· {g.subject}</span></h3>
                        <span className="font-extrabold text-2xl">{g.accuracy_pct}%</span>
                      </div>
                      <p className="text-lg mt-1">{t.wrongCountLabel}: <b>{g.wrong_count}</b> · {t.correctCountLabel}: <b>{g.correct_count}</b>{g.mastery_level ? ` · ${g.mastery_level}` : ""}</p>
                      {g.common_mistakes?.length > 0 && (
                        <>
                          <h4 className="font-bold text-lg mt-3">{t.commonMistakesLabel}</h4>
                          <ul className="list-disc pl-6 text-lg">{g.common_mistakes.map((m) => <li key={m}>{m}</li>)}</ul>
                        </>
                      )}
                      {g.key_concepts?.length > 0 && (
                        <>
                          <h4 className="font-bold text-lg mt-3">{t.keyConceptsLabel}</h4>
                          <p className="text-lg">{g.key_concepts.join(", ")}</p>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-lg text-secondary" data-testid="skill-gaps-empty">{t.noSkillGaps}</p>}
            </Section>
          )}

          {errors && (
            <Section title={t.errorAnalysisTitle} icon={XCircle} testid="parent-error-analysis">
              {errors.length ? (
                <ol className="space-y-3 list-decimal pl-6">
                  {errors.map((e, i) => (
                    <li key={`${e.question}-${i}`} className="text-lg">
                      <p className="font-bold text-xl">{e.question}</p>
                      <p className="text-secondary text-base">{e.subject} · {e.topic} · {t.wrongTimesLabel}: {e.wrong_count}</p>
                      {e.hint && <p className="mt-1"><b>{t.hintLabel}:</b> {e.hint}</p>}
                    </li>
                  ))}
                </ol>
              ) : <p className="text-lg text-secondary" data-testid="error-analysis-empty">{t.noErrors}</p>}
            </Section>
          )}

          <Section title={t.reviewTitle} icon={HelpCircle} testid="parent-review">
            {items.length ? (
              <ol className="list-decimal pl-6 space-y-2 text-lg">
                {items.map((it, i) => (
                  <li key={i}>{it.question} <span className="text-secondary text-base">({it.topic})</span></li>
                ))}
              </ol>
            ) : <p className="text-lg text-secondary">{t.noReview}</p>}
          </Section>
        </>
      )}
    </div>
  );
};
