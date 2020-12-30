% TimeTagger - Demo
% A live demo using simulated data, with a custom day as now

<style>
main, header { background: none; }
main .content {
    position: absolute;
    top: 40px; bottom: 0; left: 0; right: 0;
    padding: 0; margin: 0;  /* override centering for static position */
}
#canvas {
    position: absolute;
    top: 0; bottom: 0; left: 0; right: 0; height: 100%; width: 100%;
    border: 0; margin: 0; padding: 0; outline: none;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.4);
    border-radius: 2px;
}
@media screen and (min-width: 800px) { main .content {
    width: 100%; /* override the rule in style.css */
}}
@media screen and (min-width: 1024px) { main .content {
        left: calc(50% - 512px); right: calc(50% - 512px); width: 1024px;
}}
footer, header, #header-content {
    display: none;
}
main .content { top: 0; }
</style>

<script src='utils.js'></script>
<script src='dt.js'></script>
<script src='stores.js'></script>
<script src='dialogs.js'></script>
<script src='front.js'></script>
<script src='jspdf.js'></script>
<script src='Ubuntu-C-normal.js'></script>




<script>

// Run demo at a specific moment in time, good for making screenshots
var demodeltatime = dt.now() - new Date("2020-02-27 16:15").getTime() / 1000;
dt.now = function() { return new Date().getTime() / 1000 - demodeltatime};

window.addEventListener("load", function() {
    if (!window.browser_supported) {return;}
    window.store = new window.stores.DemoDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);
});
</script>









<!-- Force preloading the font used in the canvas -->
<span style='font-family: "Ubuntu Condensed"; color: #eee;'>demo</span>
<span class='fas' style='color: #eee;'></span>
<img id='ttlogo' alt='TimeTagger logo' src='timetagger192.png' width='2px' />

<canvas id='canvas'>This website needs a working (HTML5) canvas.</canvas>
