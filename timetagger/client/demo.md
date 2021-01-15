% TimeTagger - Demo
% A live demo using simulated data.


<script src='utils.js'></script>
<script src='dt.js'></script>
<script src='stores.js'></script>
<script src='dialogs.js'></script>
<script src='front.js'></script>
<script src='jspdf.js'></script>
<script src='Ubuntu-C-normal.js'></script>


<script>

// Uncomment to run demo at a specific moment in time, nice for making screenshots
// var demodeltatime = dt.now() - new Date("2021-01-12T16:15:00").getTime() / 1000;
// dt.now = function() { return new Date().getTime() / 1000 - demodeltatime};

window.addEventListener("load", function() {
    if (!window.browser_supported) {return;}
    window.store = new window.stores.DemoDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);
    var dialog = new dialogs.DemoInfoDialog(window.canvas);
    setTimeout(dialog.open, 200);
});
</script>


<!-- Force preloading the font used in the canvas -->
<span style='font-family: "Ubuntu Condensed"; color: #eee;'>demo</span>
<span class='fas' style='color: #eee;'></span>
<img id='ttlogo' alt='TimeTagger logo' src='timetagger192.png' width='2px' />

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>
