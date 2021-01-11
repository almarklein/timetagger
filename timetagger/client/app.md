% TimeTagger - App
% The TimeTagger application.

<script src='auth.js'></script>
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
    window.store = new window.stores.ConnectedDataStore();
    var canvas_element = document.getElementById('canvas');
    window.canvas = new window.front.TimeTaggerCanvas(canvas_element);
    // Register the service worker as soon as the user loads the app
    //if ('serviceWorker' in navigator) {
    //    navigator.serviceWorker.register('/sw.js');
    //}
    navigator.serviceWorker.addEventListener('controllerchange', function () {
        // This gets called when the browser detects a new version of
        // the service worker (when any byte has changed).
    });
});
</script>


<!-- Force preloading the font used in the canvas -->
<span style='font-family: "Ubuntu Condensed"; color: #eee;'>app</span>
<span class='fas' style='color: #eee;'></span>
<img id='ttlogo' alt='TimeTagger logo' src='timetagger192.png' width='2px' />

<canvas id='canvas'>This page needs a working (HTML5) canvas.</canvas>

<style>
#newappreload {
  visibility: hidden;
  position: fixed;
  left: 20vw;
  right: 20vw;
  bottom: 20px;
  background-color: #333;
  color: #fff;
  text-align: center;
  border-radius: 2px;
  padding: 16px;
  z-index: 9999;
}
#newappreload.show {
  visibility: visible;
  -webkit-animation: fadein 0.5s;
  animation: fadein 0.5s;
}
</style>
<div id="newappreload"><a>A new version of TimeTagger is available. Click to refresh.</a></div>
