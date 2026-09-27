import { useEffect, useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { DICT } from "@/i18n";
import { AccessibilityTopBar } from "@/components/AccessibilityTopBar";
import { BookLibrary } from "@/components/BookLibrary";
import { TutorChat } from "@/components/TutorChat";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const FONT_SIZES = ["20px", "24px", "28px"];

function App() {
  const [lang, setLang] = useState("az");
  const [theme, setTheme] = useState("light");
  const [fontStep, setFontStep] = useState(0);
  const [speed, setSpeed] = useState(1.0);
  const [books, setBooks] = useState([]);
  const [active, setActive] = useState(undefined); // undefined = library, null = general chat, obj = book

  const t = DICT[lang];

  useEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);
  useEffect(() => { document.documentElement.style.setProperty("--base-font", FONT_SIZES[fontStep]); }, [fontStep]);

  const loadBooks = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/books`);
      setBooks(res.data);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { loadBooks(); }, [loadBooks]);

  return (
    <div className="App">
      <AccessibilityTopBar {...{ t, lang, setLang, theme, setTheme, fontStep, setFontStep, speed, setSpeed }} />
      {active === undefined ? (
        <BookLibrary t={t} lang={lang} books={books} onSelect={setActive} onUploaded={loadBooks} />
      ) : (
        <TutorChat t={t} lang={lang} book={active} speed={speed} onBack={() => setActive(undefined)} />
      )}
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
