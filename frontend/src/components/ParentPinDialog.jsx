import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Lock, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PIN_RE = /^\d{4}$/;

const postJson = (path, body) =>
  fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

/** Valideyn PIN qapısı. Props: { t, onSuccess, onBack } */
export const ParentPinDialog = ({ t, onSuccess, onBack }) => {
  const [hasPin, setHasPin] = useState(null);
  const [pin, setPin] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pinRef = useRef(null);

  useEffect(() => {
    let alive = true;
    fetch(`${API}/parent/pin-status`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => alive && setHasPin(!!d.has_pin))
      .catch((err) => { console.error("PIN status failed", err); if (alive) { setHasPin(true); setError(t.pinNetworkError); } });
    return () => { alive = false; };
  }, [t]);

  useEffect(() => { if (hasPin !== null) pinRef.current?.focus(); }, [hasPin]);

  const fail = (msg) => { setError(msg); setPin(""); setConfirm(""); pinRef.current?.focus(); };

  const submit = async (e) => {
    e?.preventDefault();
    if (busy) return;
    setError("");
    if (!PIN_RE.test(pin)) return fail(t.pinMustBe4);
    if (!hasPin && pin !== confirm) return fail(t.pinMismatch);
    setBusy(true);
    try {
      if (!hasPin) {
        const r = await postJson("/parent/pin", { pin });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        onSuccess();
      } else {
        const r = await postJson("/parent/verify", { pin });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        if (d.ok) onSuccess();
        else fail(t.pinWrong);
      }
    } catch (err) {
      console.error("PIN request failed", err);
      fail(t.pinNetworkError);
    } finally { setBusy(false); }
  };

  const digits = (v) => v.replace(/\D/g, "").slice(0, 4);
  const inputCls = "w-full h-20 px-5 rounded-2xl bg-surface-2 border-solid-2 text-5xl font-bold tracking-[0.5em] text-center outline-none focus:ring-4";

  return (
    <div className="max-w-md mx-auto px-4 py-10">
      <button data-testid="pin-back-btn" onClick={onBack} aria-label={t.back}
        className="w-14 h-14 rounded-2xl bg-surface border-solid-2 flex items-center justify-center mb-6">
        <ArrowLeft size={28} />
      </button>
      <form data-testid="parent-pin-dialog" onSubmit={submit} aria-labelledby="pin-title"
        className="bg-surface border-solid-2 rounded-3xl p-6 space-y-5">
        <div className="flex items-center gap-3">
          <Lock size={36} className="text-accent shrink-0" aria-hidden="true" />
          <h1 id="pin-title" className="font-heading font-extrabold text-3xl">
            {hasPin === false ? t.pinCreateTitle : t.pinEnterTitle}
          </h1>
        </div>
        {hasPin === null ? (
          <div className="flex justify-center py-6"><Loader2 size={40} className="animate-spin text-accent" /></div>
        ) : (
          <>
            <p className="text-xl">{hasPin ? t.pinEnterDesc : t.pinCreateDesc}</p>
            <label className="block text-xl font-bold" htmlFor="parent-pin">{t.pinLabel}</label>
            <input id="parent-pin" ref={pinRef} data-testid="pin-input" type="password" inputMode="numeric"
              autoComplete={hasPin ? "current-password" : "new-password"} maxLength={4} value={pin}
              aria-label={t.pinLabel} aria-invalid={!!error} aria-describedby={error ? "pin-error" : undefined}
              onChange={(e) => setPin(digits(e.target.value))} className={inputCls} />
            {!hasPin && (
              <>
                <label className="block text-xl font-bold" htmlFor="parent-pin-confirm">{t.pinConfirmLabel}</label>
                <input id="parent-pin-confirm" data-testid="pin-confirm-input" type="password" inputMode="numeric"
                  autoComplete="new-password" maxLength={4} value={confirm} aria-label={t.pinConfirmLabel}
                  aria-invalid={!!error} onChange={(e) => setConfirm(digits(e.target.value))} className={inputCls} />
              </>
            )}
          </>
        )}
        {error && (
          <p id="pin-error" role="alert" data-testid="pin-error"
            className="text-xl font-bold rounded-2xl p-4 bg-red-100 text-red-900 border-solid-2">{error}</p>
        )}
        <button type="submit" data-testid="pin-submit-btn" disabled={busy || hasPin === null}
          className="w-full h-16 rounded-2xl bg-accent text-white accent-fg border-solid-2 font-heading font-bold text-2xl disabled:opacity-50 flex items-center justify-center gap-2">
          {busy && <Loader2 size={26} className="animate-spin" />}
          {hasPin === false ? t.pinSave : t.pinOpen}
        </button>
      </form>
    </div>
  );
};

export default ParentPinDialog;
