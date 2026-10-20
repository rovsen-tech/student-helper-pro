import { Loader2, X } from "lucide-react";

// "vocabulary" həmişə boş gəlir, ona görə burada göstərilmir.
const SECTIONS = [
  { key: "summary", title: "Qısa xülasə" },
  { key: "key_concepts", title: "Əsas anlayışlar" },
  { key: "definitions", title: "Təriflər" },
  { key: "rules", title: "Qaydalar" },
  { key: "formulas", title: "Düsturlar" },
  { key: "exam_tips", title: "İmtahan üçün vacib" },
];

export const SmartNotes = ({ notes, loading = false, onClose }) => {
  if (loading) {
    return (
      <div data-testid="smart-notes" className="flex items-center gap-3 text-lg p-4">
        <Loader2 size={22} className="animate-spin" /> Qeydlər hazırlanır...
      </div>
    );
  }
  if (!notes) return null;

  const visible = SECTIONS
    .map((s) => ({ ...s, items: (notes[s.key] ?? []).filter((x) => typeof x === "string" && x.trim()) }))
    .filter((s) => s.items.length > 0);

  return (
    <div data-testid="smart-notes" className="bg-surface border-solid-2 rounded-3xl p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-heading font-bold text-2xl truncate">📝 {notes.title ?? "Dərs qeydləri"}</h3>
        {onClose && (
          <button data-testid="smart-notes-close" onClick={onClose} aria-label="Bağla"
            className="w-11 h-11 rounded-2xl bg-surface-2 border-solid-2 flex items-center justify-center shrink-0">
            <X size={22} />
          </button>
        )}
      </div>
      {visible.length === 0 ? (
        <p className="text-lg text-secondary">Hələ qeyd ediləcək məlumat yoxdur. Dərsi davam etdir.</p>
      ) : (
        visible.map((s) => (
          <section key={s.key} data-testid={`smart-notes-${s.key}`}>
            <h4 className="font-bold text-xl mb-2">{s.title}</h4>
            <ul className="list-disc pl-6 space-y-1 text-lg leading-relaxed">
              {s.items.map((item, i) => <li key={`${s.key}-${i}`}>{item}</li>)}
            </ul>
          </section>
        ))
      )}
    </div>
  );
};

export default SmartNotes;
