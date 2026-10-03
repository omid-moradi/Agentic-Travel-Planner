"use client";

/**
 * Language context: fa (RTL) by default, switchable to en (LTR).
 * The direction is applied on a wrapper div so the html tag stays server-rendered.
 */

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { DICTS, DIRS, type DictKey, type Lang } from "./i18n";

interface LangContextValue {
  lang: Lang;
  dir: "rtl" | "ltr";
  setLang: (lang: Lang) => void;
  t: (key: DictKey) => string;
}

const LangContext = createContext<LangContextValue | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("fa");

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
  }, []);

  const value = useMemo<LangContextValue>(
    () => ({
      lang,
      dir: DIRS[lang],
      setLang,
      t: (key: DictKey) => DICTS[lang][key],
    }),
    [lang, setLang],
  );

  return (
    <LangContext.Provider value={value}>
      <div dir={DIRS[lang]} lang={lang} className="contents">
        {children}
      </div>
    </LangContext.Provider>
  );
}

export function useLang(): LangContextValue {
  const context = useContext(LangContext);
  if (!context) {
    throw new Error("useLang must be used inside <LangProvider>");
  }
  return context;
}
