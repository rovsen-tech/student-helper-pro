import { useRef, useState } from "react";
import { Upload, BookOpen, MessageCircleQuestion, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SUBJECT_COLORS = {
  Biologiya: "#16A34A", "Təbiət elmləri": "#2563EB", Riyaziyyat: "#EA580C", Tarix: "#9333EA",
};

export const BookLibrary = ({ t, lang, books, onSelect, onUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  const doUpload = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error(t.pdfOnly);
      return;
    }
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("lang", lang);
    try {
      const res = await fetch(`${API}/books/upload`, { method: "POST", body: form });
      if (!res.ok) throw new Error();
      const book = await res.json();
      toast.success(book.title);
      onUploaded();
    } catch {
      toast.error(t.uploadError);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Hero */}
      <div className="rise mb-8 rounded-3xl overflow-hidden border-solid-2 bg-surface">
        <div className="grid md:grid-cols-2 gap-0 items-center">
          <div className="p-8 md:p-10">
            <div className="inline-flex items-center gap-2 bg-surface-2 rounded-full px-4 py-2 mb-4 border-solid-2">
              <Sparkles size={20} className="text-accent" />
              <span className="font-bold text-base">Ağıllı Müəllim</span>
            </div>
            <h1 className="font-heading font-extrabold text-4xl sm:text-5xl mb-4 leading-tight">{t.tagline}</h1>
            <p className="text-secondary text-xl">{t.welcome}</p>
          </div>
          <div className="h-64 md:h-full min-h-[16rem]">
            <img src="https://images.unsplash.com/photo-1599689868384-59cb2b01bb21?crop=entropy&cs=srgb&fm=jpg&q=85&w=900"
              alt={t.heroImageAlt} className="w-full h-full object-cover" />
          </div>
        </div>
      </div>

      {/* General chat + Upload */}
      <div className="grid md:grid-cols-2 gap-5 mb-10">
        <button data-testid="general-chat-card" onClick={() => onSelect(null)} aria-label={`${t.general}: ${t.generalDesc}`}
          className="rise text-left p-6 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center shrink-0" style={{ color: "#fff" }}>
            <MessageCircleQuestion size={32} className="accent-fg" />
          </div>
          <div>
            <h3 className="font-heading font-bold text-2xl mb-1">{t.general}</h3>
            <p className="text-secondary text-lg">{t.generalDesc}</p>
          </div>
        </button>

        <div
          data-testid="upload-dropzone"
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); doUpload(e.dataTransfer.files[0]); }}
          onClick={() => !uploading && fileRef.current?.click()}
          role="button" tabIndex={0} aria-label={uploading ? t.uploading : `${t.uploadBook}: ${t.dropHint}`} aria-busy={uploading}
          onKeyDown={(e) => { if ((e.key === "Enter" || e.key === " ") && !uploading) { e.preventDefault(); fileRef.current?.click(); } }}
          className={`rise p-6 rounded-3xl border-solid-2 border-dashed flex items-center gap-4 transition-colors cursor-pointer ${dragOver ? "bg-surface-2" : "bg-surface"}`}
          style={dragOver ? { borderColor: "var(--accent)" } : {}}
        >
          <input ref={fileRef} type="file" accept="application/pdf" className="hidden" aria-label={t.uploadBook}
            data-testid="upload-input" onChange={(e) => doUpload(e.target.files[0])} />
          <div className="w-16 h-16 rounded-2xl bg-surface-2 flex items-center justify-center shrink-0 text-accent">
            {uploading ? <Loader2 size={32} className="animate-spin" /> : <Upload size={32} />}
          </div>
          <div>
            <h3 className="font-heading font-bold text-2xl mb-1">{uploading ? t.uploading : t.uploadBook}</h3>
            <p className="text-secondary text-lg">{t.dropHint}</p>
          </div>
        </div>
      </div>

      {/* Library */}
      <h2 className="font-heading font-bold text-3xl mb-5 flex items-center gap-3">
        <BookOpen size={30} className="text-accent" /> {t.library}
      </h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {books.map((b, i) => {
          const color = SUBJECT_COLORS[b.subject] || "var(--accent)";
          return (
            <button key={b.id} data-testid={`book-card-${i}`} onClick={() => onSelect(b)}
              aria-label={`${b.title} — ${t.startLesson}`}
              className="rise text-left p-6 rounded-3xl bg-surface border-solid-2 hover:-translate-y-1 transition-transform flex flex-col"
              style={{ animationDelay: `${i * 60}ms` }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="px-3 py-1 rounded-full text-base font-bold text-white" style={{ background: color }}>{b.subject || "Dərslik"}</span>
                {b.grade && <span className="text-secondary text-base font-semibold">{b.grade}</span>}
              </div>
              <h3 className="font-heading font-bold text-2xl mb-2 leading-snug">{b.title}</h3>
              <p className="text-secondary text-lg mb-4 flex-1">{b.summary}</p>
              <span className="inline-flex items-center gap-2 font-bold text-lg text-accent">
                <BookOpen size={22} /> {t.startLesson}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
