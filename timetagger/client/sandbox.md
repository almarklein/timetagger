% TimeTagger - Sandbox
% An empty app, not connected to the server, to try things out.


<script src='utils.js'></script>
<script src='dt.js'></script>
<script src='stores.js'></script>
<script src='dialogs.js'></script>
<script src='front.js'></script>
<script src='jspdf.js'></script>
<script src='Ubuntu-C-normal.js'></script>


<script>
window.addEventListener("load", function() {
    if (!window.browser_supported) {return;}
    window.store = new window.stores.SandboxDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);
    var dialog = new dialogs.SandboxInfoDialog(window.canvas);
    setTimeout(dialog.open, 200);
});
</script>


<!-- Force preloading the font used in the canvas -->
<span style='font-family: "Ubuntu Condensed"; color: #eee;'>sandbox</span>
<span class='fas' style='color: #eee;'></span>
<img id='ttlogo' alt='TimeTagger logo' src='timetagger192.png' width='2px' />

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>
