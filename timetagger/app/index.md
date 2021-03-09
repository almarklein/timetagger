% TimeTagger - App
% The TimeTagger application.

<script src='auth.js'></script>

<script>

window.addEventListener("load", function() {
    if (!window.browser_supported) {return;}
    window.store = new window.stores.ConnectedDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);

    // Register service worker, only when loading the actual app.
    register_service_worker();
});


function register_service_worker() {

    // Could disable on localhost, because localhost is also likely used for other things.
    // However, since the SW is local to /timetagger/app by default, it should be fine.
    // if (location.hostname !== "localhost" && location.hostname !== "127.0.0.1") { return; }

    // SW supported?
    if (!('serviceWorker' in navigator)) { return; }

    // Structure for the PWA installation workflow
    window.pwa = {
        sw_reg: null, // set when sw is registered
        deferred_prompt: null,  // set when browser considers this a PWA
        install: async function() {
            window.pwa.deferred_prompt.prompt();
            const { outcome } = await window.pwa.deferred_prompt.userChoice;
            window.pwa.deferred_prompt = null;
        },
        update: function () {
            if (window.pwa.sw_reg) { window.pwa.sw_reg.update(); }
        },
        show_refresh_button: function () {
            let style, html, el;
            style = 'background:#fff; color:#444; padding:0.3em; border: 1px solid #777; border-radius:4px; ';
            style += 'position:absolute; top: 34px; left:4px; font-size:80%; '
            html = "<div style='" + style + "'>";
            html += "New version available, ";
            html += "<a href='#' onclick='location.reload();'>refresh</a>";
            html += " to update.</div>"
            el = document.createElement("div");
            el.innerHTML = html;
            el = el.children[0];
            document.getElementById("canvas").parentNode.appendChild(el);
        }
    };

    // Register the service worker
    navigator.serviceWorker.register('sw.js').then(reg => { window.pwa.sw_reg = reg; });

    // Detect when the browser agrees that this is a PWA
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();  // Prevent the mini-infobar from appearing on mobile
        window.pwa.deferred_prompt = e;  // Store event for later use
    });

    // Detect when a new service worker is activated. This happens after an update
    // (or just after page load) when a new SW is found, installed, and activated.
    var page_start_time = performance.now();
    navigator.serviceWorker.addEventListener('controllerchange', function () {
        console.log("New service worker detected.")
        // Prevent continuous refresh when dev tool SW refresh is on
        if (page_start_time === null) { return; }
        if (performance.now() - page_start_time < 3000) {
            page_start_time = null;
            window.location.reload();  // User just arrived/refreshed, auto-refresh is ok
        } else {
           window.pwa.show_refresh_button();  // Prompt the user to refresh instead
        }
    });

    // Auto-update each several hours
    var nhours = 4
    window.setInterval(() => {window.pwa.update()}, nhours * 60 * 60 * 1000);
}

</script>

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>
