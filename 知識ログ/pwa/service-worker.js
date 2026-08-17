// アプリシェルのキャッシュのみ担当。GAS Web AppへのPOSTはここを経由しない
// （送信の再送はapp.js側のretry-on-loadキューが担当する）。
const CACHE_NAME = "chosaresu-log-v1";
const ASSETS = ["./", "./index.html", "./app.js", "./manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
