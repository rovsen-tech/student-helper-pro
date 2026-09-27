import { useRef, useState } from "react";
import * as Icons from "lucide-react";
import { Upload, MessageCircleQuestion, Loader2, GraduationCap, BookOpen } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Home = ({ t, lang, subjects, books, onSubject, onChat, onUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  const doUpload = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) { toast.error("PDF seç"); return; }
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("lang", lang);
    try {
      const res = await fetch(`${API}/books/upload`, { method: "POST", body: form });
      if (!res.ok) throw new Error();
      const b = await res.json();
      toast.success(b.title);
      onUploaded();
    } catch { toast.error(t.uploadError); } finally { setUploading(false); }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Hero */}
      <div className="rise mb-12 rounded-3xl overflow-hidden border-solid-2 bg-surface grid md:grid-cols-2">
        <div className="p-8 md:p-12 flex flex-col justify-center">
          <div className="inline-flex items-center gap-2 bg-surface-2 rounded-full px-4 py-2 mb-5 border-solid-2 self-start">
            <GraduationCap size={20} className="text-accent" />
            <span className="font-bold text-base">{t.subtitle}</span>
          </div>
          <h1 className="font-heading font-extrabold text-4xl sm:text-5xl lg:text-6xl mb-4 leading-tight">{t.appName}</h1>
          <p className="text-secondary text-xl">{t.tagline}</p>
        </div>
        <div className="h-64 md:h-auto min-h-[18rem]">
          <img src="https://images.unsplash.com/photo-1599689868384-59cb2b01bb21?crop=entropy&cs=srgb&fm=jpg&q=85&w=900"
            alt="student reading" className="w-full h-full object-cover" />
        </div>
      </div>

      {/* Subjects */}
      <h2 className="font-heading font-bold text-3xl mb-6 flex items-center gap-3">
        <BookOpen size={30} className="text-accent" /> {t.subjectsHeading}
      </h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-14">
        {subjects.map((s, i) => {
          const Icon = Icons[s.icon] || BookOpen;
          return (
            <button key={s.id} data-testid={`subject-card-${s.id}`} onClick={() => onSubject(s)}
              className="rise text-left p-6 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex items-start gap-4"
              style={{ animationDelay: `${i * 45}ms` }}>
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center shrink-0" style={{ background: s.color, color: "#fff" }}>
                <Icon size={32} />
              </div>
              <div className="min-w-0">
                <h3 className="font-heading font-bold text-2xl mb-1 leading-snug">{s.name}</h3>
                <p className="text-secondary text-lg leading-relaxed">{s.description}</p>
                <span className="inline-block mt-2 font-bold text-base" style={{ color: s.color }}>{s.topics.length} {t.lessonsCount}</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Tools */}
      <div className="grid md:grid-cols-2 gap-5 mb-12">
        <button data-testid="general-chat-card" onClick={() => onChat({ kind: "general" })}
          className="text-left p-6 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center shrink-0" style={{ color: "#fff" }}>
            <MessageCircleQuestion size={32} className="accent-fg" />
          </div>
          <div>
            <h3 className="font-heading font-bold text-2xl mb-1">{t.general}</h3>
            <p className="text-secondary text-lg">{t.generalDesc}</p>
          </div>
        </button>

        <div data-testid="upload-dropzone"
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); doUpload(e.dataTransfer.files[0]); }}
          onClick={() => !uploading && fileRef.current?.click()}
          className={`p-6 rounded-3xl border-solid-2 border-dashed flex items-center gap-4 cursor-pointer transition-colors ${dragOver ? "bg-surface-2" : "bg-surface"}`}
          style={dragOver ? { borderColor: "var(--accent)" } : {}}>
          <input ref={fileRef} type="file" accept="application/pdf" className="hidden" data-testid="upload-input" onChange={(e) => doUpload(e.target.files[0])} />
          <div className="w-16 h-16 rounded-2xl bg-surface-2 flex items-center justify-center shrink-0 text-accent">
            {uploading ? <Loader2 size={32} className="animate-spin" /> : <Upload size={32} />}
          </div>
          <div>
            <h3 className="font-heading font-bold text-2xl mb-1">{uploading ? t.uploading : t.uploadBook}</h3>
            <p className="text-secondary text-lg">{t.dropHint}</p>
          </div>
        </div>
      </div>

      {/* My books */}
      {books.length > 0 && (
        <>
          <h2 className="font-heading font-bold text-3xl mb-6">{t.myBooks}</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {books.map((b, i) => (
              <button key={b.id} data-testid={`book-card-${i}`} onClick={() => onChat({ kind: "book", book: b })}
                className="rise text-left p-6 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex flex-col"
                style={{ animationDelay: `${i * 45}ms` }}>
                <span className="px-3 py-1 rounded-full text-base font-bold text-white self-start mb-3" style={{ background: "var(--accent)" }}>{b.subject || "Kitab"}</span>
                <h3 className="font-heading font-bold text-2xl mb-2 leading-snug">{b.title}</h3>
                <p className="text-secondary text-lg flex-1">{b.summary}</p>
                <span className="inline-flex items-center gap-2 font-bold text-lg text-accent mt-3"><BookOpen size={22} /> {t.startLesson}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
