"use client";

import { useEffect } from "react";

/** Registers the Live Mode service worker (offline itinerary cache). */
export function ServiceWorkerRegistrar() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // Registration failing must never break the page (e.g. dev mode).
      });
    }
  }, []);
  return null;
}
