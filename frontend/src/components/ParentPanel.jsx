import { useEffect, useState } from "react";
import { ArrowLeft, BarChart3, Trophy, Flame, Star, Target, AlertTriangle, HelpCircle, Loader2 } from "lucide-react";

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

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);
    Promise.allSettled([getJson("/progress/stats"), getJson("/progress/review-questions")]).then(([s, r]) => {
      if (!alive) return;
      setStats(s.status === "fulfilled" ? s.value : null);
      setReview(r.status === "fulfilled" ? r.value : null);
      if (s.status === "rejected") { console.error("Stats failed", s.reason); setError(true); }
      if (r.status === "rejected") console.error("Review failed", r.reason);
      setLoading(false);
    });
    return () => { alive = false; };
  }, [studentId]);

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
