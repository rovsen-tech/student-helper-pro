import * as Icons from "lucide-react";
import { ArrowLeft, BookOpen, Volume2 } from "lucide-react";

export const SubjectView = ({ t, subject, onBack, onLesson }) => {
  const Icon = Icons[subject.icon] || BookOpen;
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-10">
        <button data-testid="subject-back-btn" onClick={onBack}
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

      <h2 className="font-heading font-bold text-2xl mb-6">{t.chooseLesson}</h2>
      <div className="grid sm:grid-cols-2 gap-4">
        {subject.topics.map((topic, i) => (
          <button key={topic} data-testid={`lesson-card-${i}`} onClick={() => onLesson(topic)}
            className="rise text-left p-5 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex items-center gap-4"
            style={{ animationDelay: `${i * 50}ms` }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 font-heading font-extrabold text-2xl"
              style={{ background: subject.color, color: "#fff" }}>{i + 1}</div>
            <span className="font-heading font-bold text-xl leading-snug flex-1">{topic}</span>
            <Volume2 size={24} style={{ color: subject.color }} />
          </button>
        ))}
      </div>
    </div>
  );
};
