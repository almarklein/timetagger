% TimeTagger - Demo
% A live demo using simulated data.



<script>

window.addEventListener("load", function() {
    if (!window.browser_supported) {return;}
    window.store = new window.stores.DemoDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);

    // Notify user that this is the Demo
    var dialog = new dialogs.DemoInfoDialog(window.canvas);
    setTimeout(dialog.open, 200);

    // Enable auto-update on localhost for easy dev
    if (location.hostname == "localhost" && location.hostname == "127.0.0.1") {
        enable_auto_update();
    }
});

// Uncomment to run demo at a specific moment in time, nice for making screenshots
// var demodeltatime = dt.now() - new Date("2021-01-12T16:15:00").getTime() / 1000;
// dt.now = function() { return new Date().getTime() / 1000 - demodeltatime};


function enable_auto_update() {

    // SW supported?
    if (!('serviceWorker' in navigator)) { return; }

    // Structure for the PWA workflow
    window.pwa = {
        sw_reg: null, // set when sw is registered
        update: function () {
            if (window.pwa.sw_reg) { window.pwa.sw_reg.update(); }
        },
    };

    // Register the service worker
    navigator.serviceWorker.register('sw.js').then(reg => { window.pwa.sw_reg = reg; });

    // Detect when a new service worker is activated. This happens after an update
    // (or just after page load) when a new SW is found, installed, and activated.
    var page_start_time = performance.now();
    navigator.serviceWorker.addEventListener('controllerchange', function () {
        console.log("New service worker detected.")
        if (page_start_time === null) {
            return;  // prevent continuous refresh when dev tool SW refresh is on
        } else {
            window.location.reload();
        }
        page_start_time = null;
    });

    // Do an update after switching to page visible
    window.document.addEventListener("visibilitychange", function () { pwa.update(); });
}
</script>

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>
