% TimeTagger - Sandbox
% An empty app, not connected to the server, to try things out.



<script>

window.addEventListener("load", function() {
    if (!window.browser_supported) {return;}
    window.store = new window.stores.SandboxDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);

    // Notify user that this is the Sandbox
    var dialog = new dialogs.SandboxInfoDialog(window.canvas);
    setTimeout(dialog.open, 200);
});
</script>

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>
