import { Minus, Plus, Sun, Moon, Contrast, Volume2, GraduationCap, BarChart3 } from "lucide-react";

const THEMES = [
  { id: "light", icon: Sun, key: "themeLight" },
  { id: "amber", icon: Moon, key: "themeAmber" },
  { id: "contrast", icon: Contrast, key: "themeContrast" },
];
const SPEEDS = [0.8, 1.0, 1.2];

export const AccessibilityTopBar = ({ t, lang, setLang, theme, setTheme, fontStep, setFontStep, speed, setSpeed, onOpenParent }) => {
  return (
    <header
      data-testid="accessibility-topbar"
      className="sticky top-0 z-50 bg-surface border-b-2 border-solid-2"
      style={{ borderBottomColor: "var(--border)" }}
    >
      <div className="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-accent flex items-center justify-center accent-fg" style={{ color: "#fff" }}>
            <GraduationCap size={28} />
          </div>
          <span className="font-heading font-extrabold text-2xl">{t.appName}</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Font size */}
          <div className="flex items-center gap-1 bg-surface-2 rounded-2xl p-1 border-solid-2">
            <button data-testid="font-decrease-btn" aria-label={t.fontDecrease} onClick={() => setFontStep(Math.max(0, fontStep - 1))}
              className="w-11 h-11 rounded-xl flex items-center justify-center hover:bg-accent hover:text-white transition-colors">
              <Minus size={22} />
            </button>
            <span className="font-heading font-bold text-lg w-6 text-center">A</span>
            <button data-testid="font-increase-btn" aria-label={t.fontIncrease} onClick={() => setFontStep(Math.min(2, fontStep + 1))}
              className="w-11 h-11 rounded-xl flex items-center justify-center hover:bg-accent hover:text-white transition-colors">
              <Plus size={22} />
            </button>
          </div>

          {/* Speed */}
          <div className="flex items-center gap-1 bg-surface-2 rounded-2xl p-1 border-solid-2" title={t.speed}>
            <Volume2 size={20} className="ml-2 text-secondary" />
            {SPEEDS.map((s) => (
              <button key={s} data-testid={`speed-${s}-btn`} onClick={() => setSpeed(s)}
                className={`h-11 px-3 rounded-xl font-bold text-base transition-colors ${speed === s ? "bg-accent text-white accent-fg" : "hover:bg-surface"}`}>
                {s}x
              </button>
            ))}
          </div>

          {/* Theme */}
          <div className="flex items-center gap-1 bg-surface-2 rounded-2xl p-1 border-solid-2">
            {THEMES.map((th) => {
              const Icon = th.icon;
              return (
                <button key={th.id} data-testid={`theme-${th.id}-btn`} aria-label={t[th.key]} title={t[th.key]} onClick={() => setTheme(th.id)}
                  className={`w-11 h-11 rounded-xl flex items-center justify-center transition-colors ${theme === th.id ? "bg-accent text-white accent-fg" : "hover:bg-surface"}`}>
                  <Icon size={22} />
                </button>
              );
            })}
          </div>

          {/* Language */}
          <div className="flex items-center gap-1 bg-surface-2 rounded-2xl p-1 border-solid-2">
            {["az", "tr"].map((l) => (
              <button key={l} data-testid={`lang-${l}-btn`} onClick={() => setLang(l)}
                className={`h-11 px-4 rounded-xl font-bold text-base transition-colors ${lang === l ? "bg-accent text-white accent-fg" : "hover:bg-surface"}`}>
                {l.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Parent panel */}
          <button data-testid="parent-panel-btn" onClick={onOpenParent} title={t.parent} aria-label={t.parent}
            className="h-[52px] px-4 rounded-2xl bg-surface-2 border-solid-2 flex items-center gap-2 font-bold text-base hover:bg-accent hover:text-white transition-colors">
            <BarChart3 size={22} /> <span className="hidden sm:inline">{t.parent}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
