// Aktiv şagird profili: localStorage-da saxlanılır və backend-ə gedən BÜTÜN
// sorğulara (fetch + axios) `X-Student-Id` başlığı kimi əlavə olunur.
import axios from "axios";

const KEY = "agilli-ders-student-id";
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
export const DEFAULT_STUDENT = "default";

export const getStudentId = () => {
  try { return localStorage.getItem(KEY) || DEFAULT_STUDENT; } catch { return DEFAULT_STUDENT; }
};

export const setStudentId = (id) => {
  try { localStorage.setItem(KEY, id || DEFAULT_STUDENT); } catch { /* private mode */ }
};

const isBackend = (url) => {
  const u = typeof url === "string" ? url : url?.url || "";
  return u.startsWith(`${BACKEND_URL}/api`) || u.startsWith("/api");
};

let installed = false;
export const installStudentHeader = () => {
  if (installed || typeof window === "undefined") return;
  installed = true;
  const original = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    if (!isBackend(input)) return original(input, init);
    const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
    if (!headers.has("X-Student-Id")) headers.set("X-Student-Id", getStudentId());
    return original(input, { ...init, headers });
  };
  axios.interceptors.request.use((config) => {
    if (isBackend(config.url)) {
      config.headers = config.headers || {};
      config.headers["X-Student-Id"] = getStudentId();
    }
    return config;
  });
};
