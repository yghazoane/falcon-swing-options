import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { DICTIONARIES, type DictKey } from "./dict";

export type Lang = "ar" | "en";
const STORAGE_KEY = "fmi-lang";

interface I18nValue {
  lang: Lang;
  dir: "rtl" | "ltr";
  setLang: (l: Lang) => void;
  t: (key: DictKey, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("ar");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "ar") setLangState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    window.localStorage.setItem(STORAGE_KEY, l);
  }, []);

  const t = useCallback(
    (key: DictKey, vars?: Record<string, string | number>) => {
      let s: string = DICTIONARIES[lang][key] ?? DICTIONARIES.en[key] ?? key;
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
      return s;
    },
    [lang],
  );

  const value = useMemo<I18nValue>(
    () => ({ lang, dir: lang === "ar" ? "rtl" : "ltr", setLang, t }),
    [lang, setLang, t],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}

/** Translate a dynamic note/status key safely, falling back to the raw string. */
export function useDynamicT() {
  const { t } = useI18n();
  return (key: string) => {
    const k = key as DictKey;
    return k in DICTIONARIES.en ? t(k) : key;
  };
}
