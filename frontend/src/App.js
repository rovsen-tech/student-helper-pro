import { useEffect, useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { DICT } from "@/i18n";
import { AccessibilityTopBar } from "@/components/AccessibilityTopBar";
import { Home } from "@/components/Home";
import { SubjectView } from "@/components/SubjectView";
import { ParentPanel } from "@/components/ParentPanel";
import { TutorChat } from "@/components/TutorChat";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const FONT_SIZES = ["20px", "24px", "28px"];

function App() {
  const [lang, setLang] = useState("az");
  const [theme, setTheme] = useState("light");
  const [fontStep, setFontStep] = useState(0);
  const [speed, setSpeed] = useState(1.0);
  const [voice, setVoice] = useState(() => localStorage.getItem("voice") || "coral");
  const [sid] = useState(() => {
    let s = localStorage.getItem("sid");
    if (!s) { s = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2)); localStorage.setItem("sid", s); }
    return s;
  });
  const [books, setBooks] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [view, setView] = useState({ type: "home" });

  const t = DICT[lang];

  useEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);
  useEffect(() => { document.documentElement.style.setProperty("--base-font", FONT_SIZES[fontStep]); }, [fontStep]);
  useEffect(() => { localStorage.setItem("voice", voice); }, [voice]);

  const loadBooks = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/books`);
      setBooks(res.data);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    loadBooks();
    axios.get(`${API}/subjects`).then((r) => setSubjects(r.data)).catch(() => {});
  }, [loadBooks]);

  return (
    <div className="App">
      <AccessibilityTopBar {...{ t, lang, setLang, theme, setTheme, fontStep, setFontStep, speed, setSpeed, voice, setVoice, onOpenParent: () => setView({ type: "parent" }) }} />
      {view.type === "home" && (
        <Home t={t} lang={lang} subjects={subjects} books={books}
          onSubject={(s) => setView({ type: "subject", subject: s })}
          onChat={(ctx) => setView({ type: "chat", ctx: { ...ctx, sid }, from: { type: "home" } })}
          onUploaded={loadBooks} />
      )}
      {view.type === "subject" && (
        <SubjectView t={t} subject={view.subject}
          onBack={() => setView({ type: "home" })}
          onLesson={(lesson) => setView({ type: "chat", ctx: { kind: "lesson", subject: view.subject.name, topic: lesson.title, lessonId: lesson.id || null, sid }, from: { type: "subject", subject: view.subject } })} />
      )}
      {view.type === "chat" && (
        <TutorChat t={t} lang={lang} ctx={view.ctx} speed={speed} voice={voice}
          onBack={() => setView(view.from || { type: "home" })} />
      )}
      {view.type === "parent" && (
        <ParentPanel t={t} subjects={subjects} onBack={() => setView({ type: "home" })} />
      )}
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
