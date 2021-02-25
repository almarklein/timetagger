// Service worker for the TimeTagger app. The primary purpose of this SW is to make the
// app usable offline, which is also a prerequisite for a PWA. Many approaches are
// possible, with each have their implications, making this quite hard to do well.
//
// I've now opted for a simple cache-first approach, where the server will set the
// currentCacheName to a hash of the assets so that the SW is automatically renewed
// when a change is made. Some advantages:
// * This SW script is quite simple.
// * The app Just Works offline.
// * A new SW means a new version, we can use that to notify the user to refresh.
//
// A note of warning: when doing rolling deploys, the server may produce a mix of old and
// new assets. In the event that the SW installs at that moment, the app may be left in a weird
// state, and the user won't be able to fix it by refreshing the page.
// So don't do rolling deploys when using this SW.
//
// Another approach I considered is network-first, which tries to behave like a normal
// website, but falls back to the cache when the fetch fails. This seems a "simple" behavior,
// but becomes rather complicated to implement, since you want to move in and out of offline-mode,
// and cancel running fetches when entering offline-mode. It also makes loading the app slow
// when being offline.

// The cache name. The server should replace this name with a new name, which must have
// the "timetagger" prefix, and which should include a stable hash of the assets.
var currentCacheName = 'timetagger_cache';

// The assets to cache upon installation. By default nothing is cached, making this SW a no-op.
// The server should replace this with a list of assets (sorted, for consistency).
var assets = [];

// Register the callbacks
self.addEventListener('install', event => { self.skipWaiting();  event.waitUntil(on_install(event)); });
self.addEventListener('activate', event => { event.waitUntil(on_activate(event)); });
self.addEventListener('fetch', on_fetch);

async function on_install(event) {
    console.log('[SW] Installling new app ' + currentCacheName);
    let cache = await caches.open(currentCacheName);
    await cache.addAll(assets.map(asset => "./" + asset));
}

async function on_activate(event) {
    let cacheNames = await caches.keys();
    for (let cacheName of cacheNames) {
        if (cacheName.startsWith("timetagger") && cacheName != currentCacheName) {
            await caches.delete(cacheName);
        }
    }
    await clients.claim();
}

function on_fetch(event) {
    var requestURL = new URL(event.request.url);
    if (
        (requestURL.origin == location.origin) &&
        (requestURL.pathname.indexOf('/api/') < 0) &&
        (assets.length > 0)
    ) {
       event.respondWith(cache_or_network(event));
    }  // else do a normal fetch

}

async function cache_or_network(event) {
    let cache = await caches.open(currentCacheName);
    let response = await cache.match(event.request);
    if (!response) {
        response = await fetch(event.request);
    }
    return response;
}
