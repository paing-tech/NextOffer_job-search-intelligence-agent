// Minimal service worker — its presence (with a fetch handler) makes the app
// installable, which is what unlocks the Web Share Target on Android. No caching.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {
  // pass-through: let the network handle every request
});
