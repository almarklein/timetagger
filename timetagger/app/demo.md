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

    // In the demo, enter dev-mode when serving on localhost
    if (location.hostname == "localhost" || location.hostname == "127.0.0.1") {
        enable_check_update_on_dbl_click();
    }
});


function set_demotime() {
    // Call to run demo at a specific moment in time, nice for making screenshots
    var demodeltatime = dt.now() - new Date("2021-03-11T16:15:00").getTime() / 1000;
    dt.now = function() { return new Date().getTime() / 1000 - demodeltatime};
}


function enable_check_update_on_dbl_click() {
    // More of a dev-mode so we can make a change, restart server,
    // and then double-click in app to auto-refresh when new version is detected.

    // SW supported?
    if (!('serviceWorker' in navigator)) { return; }

    // Structure for the PWA workflow
    window.pwa = {
        sw_reg: null, // set when sw is registered

        update: function () {
            console.log("Checking for update ...")
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
        // Prevent continuous refresh when dev tool SW refresh is on
        if (page_start_time === null) { return; }
        if (performance.now() - page_start_time < 3000) {
            page_start_time = null;
            window.location.reload();  // User just arrived/refreshed, auto-refresh is ok
        }
    });

    // Double-click invokes an update that will auto-refresh when a new version is found
    document.body.ondblclick = function ()  {
        page_start_time = performance.now();
        window.pwa.update();
    };
}
</script>

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>
