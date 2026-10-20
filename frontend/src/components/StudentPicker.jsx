import { useEffect, useState } from "react";
import { UserRound, Plus } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Hər uşağın öz profili: XP, quiz, irəliləyiş və söhbətlər ayrıca saxlanılır.
export const StudentPicker = ({ studentId, onChange }) => {
  const [students, setStudents] = useState([]);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");

  const load = () =>
    fetch(`${API}/students`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((list) => {
        setStudents(list);
        if (!list.some((s) => s.id === studentId)) onChange("default");
      })
      .catch((e) => console.error("Students load failed", e));

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    const n = name.trim();
    if (!n) return;
    try {
      const r = await fetch(`${API}/students`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: n }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);
      setName(""); setAdding(false);
      await load();
      onChange(data.id);
      toast.success(`Xoş gəldin, ${data.name}! 👋`);
    } catch (err) {
      toast.error(typeof err.message === "string" ? err.message : "Profil yaradıla bilmədi");
    }
  };

  return (
    <section aria-label="Kim öyrənir?" data-testid="student-picker"
      className="bg-surface border-solid-2 rounded-3xl p-4 mt-6 flex flex-wrap items-center gap-3">
      <span className="font-heading font-bold text-xl flex items-center gap-2">
        <UserRound size={26} className="text-accent" /> Kim öyrənir?
      </span>
      {students.map((s) => (
        <button key={s.id} type="button" onClick={() => onChange(s.id)} aria-pressed={s.id === studentId}
          data-testid={`student-${s.id}`}
          className={`px-4 py-2 rounded-2xl text-lg font-bold border-solid-2 ${s.id === studentId ? "bg-accent text-white accent-fg" : "bg-surface-2"}`}>
          {s.name}
        </button>
      ))}
      {adding ? (
        <form onSubmit={create} className="flex gap-2">
          <input autoFocus value={name} maxLength={40} onChange={(e) => setName(e.target.value)}
            aria-label="Uşağın adı" placeholder="Uşağın adı" data-testid="student-name-input"
            className="px-3 py-2 rounded-2xl text-lg border-solid-2 bg-surface-2" />
          <button type="submit" className="px-4 py-2 rounded-2xl text-lg font-bold bg-accent text-white accent-fg">Yarat</button>
          <button type="button" onClick={() => setAdding(false)} className="px-3 py-2 rounded-2xl text-lg border-solid-2">Ləğv et</button>
        </form>
      ) : (
        <button type="button" onClick={() => setAdding(true)} data-testid="student-add"
          className="px-4 py-2 rounded-2xl text-lg font-bold border-solid-2 bg-surface-2 flex items-center gap-1">
          <Plus size={20} /> Yeni profil
        </button>
      )}
    </section>
  );
};

export default StudentPicker;
