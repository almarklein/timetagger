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

// The cache name. Update this name to trigger a clean cache.
var currentCacheName = 'timetagger-cache-v2';


/***** installation *****/

self.addEventListener('install', function(event) {
  console.log('[Service Worker] Install ' + currentCacheName);
  self.skipWaiting();  // proceed to activate
  // Pre-cache, so that the user agent can see we support off-line
  //const cache = await caches.open(currentCacheName);
  //await cache.addAll(["/app"]);
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(should_delete_cache).map(function(cacheName) {
          console.log('[Service Worker] clear cache: ' + cacheName);
          return caches.delete(cacheName);
        })
      );
    })
  );
});

function should_delete_cache(cacheName) {
    // Return true if you want to remove this cache, but remember that
    // caches are shared across the whole origin
    if (cacheName == currentCacheName) { return false; }
    return true;
}


/***** Handling requests *****/

var offlinemode = false;  // Whether to load supporting assets via cache

self.addEventListener('fetch', function (event) {
  var requestURL = new URL(event.request.url);

  if (requestURL.origin == location.origin) {

    if (requestURL.pathname == '/stub') {
        // At can use this to test for new sw version
        return fetch(event.request);
    } else if (requestURL.pathname.startsWith('/api/')) {
        // API calls should not use cache
        return fetch(event.request);
    } else if (requestURL.pathname.indexOf(".") >= 0) {
        // For "static" resources, use cache if in offline mode, otherwise use network
        if (offlinemode) {
            return cache_or_network(event);
        } else {
            return network_then_cache(event, false);
        }
    } else if (requestURL.pathname == '/app') {
        // For some pages: call out to network and save to cache. Use cache as fallback.
        return network_then_cache(event, true);
    } else {
        // Other pages do not cache
        return fetch(event.request);
    }

  } else {
    // Outside this site
    return fetch(event.request);
  }

});

function cache_or_network(event) {
    console.log('[Service Worker] load from cache (or network): '+event.request.url);
    return event.respondWith(
        caches.match(event.request)
        .then(function (response) {
            return response || fetch(event.request);
        })
    );
}

function network_then_cache(event, set_offlinemode) {
    return event.respondWith(
        fetch(event.request).then(function(response) {
            // console.log('[Service Worker] Fetched and cached: '+event.request.url);
            if (set_offlinemode) { offlinemode = false; }
            return caches.open(currentCacheName).then(function(cache) {
            cache.put(event.request, response.clone());
            return response;
            });
        }, function(error) {
            console.log('[Service Worker] fallback to cache: '+event.request.url);
            if (set_offlinemode) { offlinemode = true; }
            return caches.match(event.request);
        })
    );
}
