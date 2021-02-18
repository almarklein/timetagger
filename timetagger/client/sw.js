// The idea of this service worker is to make it possible to use the app
// off-line. Multiple approaches are possible and have been considered. The
// current approach requires little changes to other parts of the website.
// The idea is that we use network-first so that we always get an up-to-date
// site on a refresh. However, we also cache the /app page and all supporting
// assets. When there is no internet, the network requests fail, and we use
// the cache instead. Only doing this would make the site slow, since each
// request times out first. Therefore we go into "offline mode" when fetching
// the /app page fails. We (currently) do not cache other pages, because the
// user may not have visited these, and may as such be outdated. Checking when
// a new version of the app is available can be done via the service worker,
// or in any other way - this approach allows decoupling that quite nicely.

// The cache name (deliberately not valid JS syntax). Update this name to trigger a clean cache.
// This needs to be set by the server. We MUST change it when any of the assets
// change. It's pretty safe to simply set it a different value each server startup.
var currentCacheName = 'CACHENAME';
// TODO: prefix the cachename so we don't delete caches intended for other apps on the same domain

/***** installation *****/


// Assets to fetch on installation of the SW. At least include /app, because
// browsers try to fetch start_url in offline mode as a test for PWA compliance.
var assets_prefetch = [ASSETS];

self.addEventListener('install', event => {    
    self.skipWaiting();  // Don't wait until the previous SW controls zero clients
    event.waitUntil(on_install(event));
});

self.addEventListener('activate', function(event) {
    event.waitUntil(on_activate(event));
});

async function on_install(event) {
    console.log('[SW] Install ' + currentCacheName);  
    let cache = await caches.open(currentCacheName);
    await cache.addAll(assets_prefetch);  
}

async function on_activate(event) {
    let cacheNames = await caches.keys();
    for (let cacheName of cacheNames) {
        if (cacheName != currentCacheName) {
          console.log('[SW] clear cache: ' + cacheName);
          await caches.delete(cacheName);
        }
    }
    await clients.claim();
}


/***** Handling requests *****/


self.addEventListener('fetch', function (event) {
  var requestURL = new URL(event.request.url);
  if (requestURL.origin != location.origin) {
    return fetch(event.request);  // Outside this site
  } else if (requestURL.pathname.indexOf('/api/') >= 0) {    
    return fetch(event.request);  // API calls should not use cache
  } else if (requestURL.pathname.indexOf(".") >= 0) {
    return respond_via_cache(event);
  } else if (requestURL.pathname.endsWith('/app')) {
    return respond_via_cache(event);
  } else {    
    return fetch(event.request);  // Other pages do not cache
  }

});


// Respond from cache. If not in cache, do a fetch and store the result in the cache.
function respond_via_cache(event) {
  event.respondWith(
    caches.match(event.request).then(cacheRes => {
      return cacheRes || fetch(event.request).then(fetchRes => {
        return caches.open(currentCacheName).then(cache => {
          cache.put(event.request.url, fetchRes.clone());
          return fetchRes;
        })
      });
    })
  );
}
