/**
 * The Live Mode service worker: cache-first for trips and static assets so
 * the itinerary stays readable offline (the master prompt's PWA requirement).
 *
 * Strategy: cache-first for GETs, network otherwise. The API responses are
 * cached under their full URL; a failed fetch falls back to the cache so a
 * trip page keeps working in a tunnel or on a plane.
 */

const CACHE = "travel-planner-v1";
const PRECACHE = ["/", "/manifest.json", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(request);
      const network = fetch(request)
        .then((response) => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
