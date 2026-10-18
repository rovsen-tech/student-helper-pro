import { useEffect, useState } from "react";
import { Flame, Trophy, BookCheck, Target, Loader2 } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Stat = ({ icon: Icon, label, value, testid }) => (
  <div className="flex items-center gap-3 bg-surface-2 border-solid-2 rounded-2xl px-4 py-3">
    <Icon size={28} className="text-accent shrink-0" />
    <div>
      <p className="text-2xl font-bold leading-none" data-testid={testid}>{value}</p>
      <p className="text-base text-secondary">{label}</p>
    </div>
  </div>
);

export const ProgressWidget = () => {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(false);
  const [barPct, setBarPct] = useState(0);

  useEffect(() => {
    let alive = true;
    fetch(`${API}/progress/stats`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => { if (alive) { setStats(d); setTimeout(() => alive && setBarPct(d.level_progress_pct ?? 0), 60); } })
      .catch((err) => { console.error("Progress stats failed", err); if (alive) setError(true); });
    return () => { alive = false; };
  }, []);

  if (error) return null;
  if (!stats) {
    return (
      <div data-testid="progress-widget" className="flex items-center gap-2 text-lg p-4">
        <Loader2 className="animate-spin" size={22} /> Yüklənir...
      </div>
    );
  }

  const empty = !stats.total_xp && !stats.lessons_complete && !stats.quiz_attempts;

  return (
    <section data-testid="progress-widget" aria-label="Mənim irəliləyişim" className="bg-surface border-solid-2 rounded-3xl p-5 mt-8">
      {empty ? (
        <p data-testid="progress-empty" className="font-heading font-bold text-2xl text-center">Öyrənməyə başla! 🚀</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <h3 className="font-heading font-bold text-2xl" data-testid="progress-level">
              <Trophy size={26} className="inline mr-2 text-accent" />{stats.level}
            </h3>
            <span className="text-xl font-bold" data-testid="progress-xp">
              {stats.total_xp} XP{stats.level_max ? ` / ${stats.level_max}` : ""}
            </span>
          </div>
          <div className="w-full h-5 rounded-full bg-surface-2 border-solid-2 overflow-hidden" role="progressbar"
            aria-valuemin={0} aria-valuemax={100} aria-valuenow={barPct} aria-label="Növbəti səviyyəyə qədər">
            <div className="h-full bg-accent transition-all duration-1000 ease-out" style={{ width: `${barPct}%` }} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
            <Stat icon={Flame} label="ardıcıl gün" value={`${stats.streak_days} 🔥`} testid="progress-streak" />
            <Stat icon={BookCheck} label="bitmiş dərs" value={stats.lessons_complete} testid="progress-lessons" />
            <Stat icon={Target} label="quiz nəticəsi" value={`${stats.quiz_correct_pct}%`} testid="progress-quiz" />
          </div>
          {stats.badges?.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4" data-testid="progress-badges">
              {stats.badges.map((b) => (
                <span key={b} className="px-3 py-1 rounded-full bg-accent text-white accent-fg font-bold text-base">🏅 {b}</span>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
};

export default ProgressWidget;
