import { useRef, useState, useCallback } from "react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export function useTTS(lang, speed) {
  const [speakingId, setSpeakingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    window.speechSynthesis?.cancel();
    setSpeakingId(null);
    setLoading(false);
  }, []);

  const speak = useCallback(async (text, id) => {
    stop();
    if (!text) return;
    setSpeakingId(id);
    setLoading(true);
    try {
      const res = await fetch(`${API}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, lang, speed }),
      });
      if (!res.ok) throw new Error("tts failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { setSpeakingId(null); URL.revokeObjectURL(url); };
      audio.onplay = () => setLoading(false);
      await audio.play();
    } catch (e) {
      // Fallback to browser speech synthesis
      try {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = lang === "az" ? "az-AZ" : "tr-TR";
        u.rate = speed;
        u.onend = () => setSpeakingId(null);
        setLoading(false);
        window.speechSynthesis.speak(u);
      } catch {
        setSpeakingId(null);
        setLoading(false);
      }
    }
  }, [lang, speed, stop]);

  return { speak, stop, speakingId, loading };
}
