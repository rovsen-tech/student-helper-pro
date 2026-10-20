import { useEffect, useState } from "react";
import * as Icons from "lucide-react";
import { ArrowLeft, BookOpen, Volume2, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const SubjectView = ({ t, subject, onBack, onLesson }) => {
  const Icon = Icons[subject.icon] || BookOpen;
  const [textbook, setTextbook] = useState(null);
  const [sectionLessons, setSectionLessons] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API}/textbooks/${subject.id}`);
        const tbs = await res.json();
        const tb = Array.isArray(tbs) && tbs.length ? tbs[0] : null;
        if (!active) return;
        setTextbook(tb);
        if (tb) {
          const map = {};
          for (const sec of tb.sections) {
            const lr = await fetch(`${API}/lessons/${tb.id}/${sec.id}`);
            map[sec.id] = await lr.json();
          }
          if (active) setSectionLessons(map);
        }
      } catch (err) {
        console.error("textbook load failed", err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [subject.id]);

  const LessonBtn = ({ title, id, idx }) => (
    <button data-testid={`lesson-card-${idx}`} onClick={() => onLesson({ id, title })}
      className="rise text-left p-5 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex items-center gap-4 w-full"
      style={{ animationDelay: `${idx * 40}ms` }}>
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 font-heading font-extrabold text-2xl"
        style={{ background: subject.color, color: "#fff" }}>{idx + 1}</div>
      <span className="font-heading font-bold text-xl leading-snug flex-1">{title}</span>
      <Volume2 size={24} style={{ color: subject.color }} />
    </button>
  );

  let flat = -1;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-10">
        <button data-testid="subject-back-btn" onClick={onBack} aria-label={t.back}
          className="w-12 h-12 rounded-2xl bg-surface border-solid-2 flex items-center justify-center hover:bg-surface-2 transition-colors shrink-0">
          <ArrowLeft size={26} />
        </button>
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center shrink-0" style={{ background: subject.color, color: "#fff" }}>
          <Icon size={34} />
        </div>
        <div className="min-w-0">
          <h1 className="font-heading font-extrabold text-3xl sm:text-4xl leading-tight">{subject.name}</h1>
          <p className="text-secondary text-lg">{subject.description}</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 size={38} className="animate-spin text-accent" /></div>
      ) : textbook ? (
        <div data-testid="textbook-view">
          <div className="flex items-center gap-2 mb-6 flex-wrap">
            <span className="px-3 py-1 rounded-full text-base font-bold text-white" style={{ background: subject.color }}>{textbook.title}</span>
            <span className="text-secondary text-base font-semibold">{textbook.grade}</span>
          </div>
          <div className="space-y-8">
            {textbook.sections.map((sec) => (
              <div key={sec.id} data-testid={`section-${sec.id}`}>
                <h2 className="font-heading font-bold text-2xl mb-4">{sec.title}</h2>
                <div className="grid sm:grid-cols-2 gap-4">
                  {(sectionLessons[sec.id] || []).map((les) => { flat += 1; return <LessonBtn key={les.id} title={les.title} id={les.id} idx={flat} />; })}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <>
          <h2 className="font-heading font-bold text-2xl mb-6">{t.chooseLesson}</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {subject.topics.map((topic, i) => <LessonBtn key={topic} title={topic} idx={i} />)}
          </div>
        </>
      )}
    </div>
  );
};
