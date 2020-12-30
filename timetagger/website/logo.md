% TimeTagger - Logo
% A logo generator.

<style>

#canvas {
    
    
    box-shadow: 0 0 32px rgba(0, 0, 0, 0.4);
}

</style>

<script src='utils.js'></script>
<script>
"use strict";

window.onload = function () {
    var canvas_element = document.getElementById('canvas');
    window.canvas = new LogoCanvas(canvas_element);
    
    var range = document.getElementById('sizerange');
    var label = document.getElementById('sizelabel');
    range.oninput = function () {
        var size = range.value;
        canvas_element.style.width = canvas_element.style.height = size;
        canvas_element.width = canvas_element.height = size;
        window.canvas._on_js_resize_event();
    };
    
    var whitecheck = document.getElementById('whitecheck');
    whitecheck.oninput = function () {
        window.logocolor = whitecheck.checked ? "#fff" : '#000';
        window.canvas._on_js_resize_event();
    };
    
    whitecheck.oninput();
    window.setTimeout(range.oninput, 10);
};

var _pyfunc_op_instantiate = function (ob, args) { // nargs: 2
    if ((typeof ob === "undefined") ||
            (typeof window !== "undefined" && window === ob) ||
            (typeof global !== "undefined" && global === ob))
            {throw "Class constructor is called as a function.";}
    for (var name in ob) {
        if (Object[name] === undefined &&
            typeof ob[name] === 'function' && !ob[name].nobind) {
            ob[name] = ob[name].bind(ob);
            ob[name].__name__ = name;
        }
    }
    if (ob.__init__) {
        ob.__init__.apply(ob, args);
    }
};

var LogoCanvas = function () {
    _pyfunc_op_instantiate(this, arguments);
}
LogoCanvas.prototype = Object.create(utils.BaseCanvas.prototype);
LogoCanvas.prototype._base_class = utils.BaseCanvas.prototype;
LogoCanvas.prototype.__name__ = "LogoCanvas";

LogoCanvas.prototype.__init__ = function (canvas) {
    LogoCanvas.prototype._base_class.__init__.call(this, canvas);
};

/* ===== The draw function ===== */

function topointoncircle(ctx, cx, cy, r, a) {
    ctx.lineTo(cx + Math.cos(a * Math.PI) * r, cy + Math.sin(a * Math.PI) * r);
}

function draw_cone(ctx, cx, cy, a1, a2, r1, r2) {
    topointoncircle(ctx, cx, cy, r1, a1);
    topointoncircle(ctx, cx, cy, r2, a1);
    ctx.arc(cx, cy, r2, a1 * Math.PI, a2 * Math.PI);
    topointoncircle(ctx, cx, cy, r2, a2);
    topointoncircle(ctx, cx, cy, r1, a2);
}

function draw_cone_fill(ctx) {
    ctx.beginPath(); draw_cone.apply(this, arguments); ctx.closePath(); ctx.fill();
}

LogoCanvas.prototype.on_draw = function (ctx) {
    
    // Set label
    var label = document.getElementById('sizelabel')
    label.innerHTML = this.w + "x" + this.h;
    if (this.pixel_ratio != 1) {
        label.innerHTML += " Warning: pixel ratio is " + this.pixel_ratio; 
    }
    
    // Clear background
    ctx.clearRect(0, 0, this.w, this.h);
    
    // Prepare vars
    var s = this.w;
    var r = 0.45 * s;
    var cx = s/2;
    var cy = s/2;
    
    ctx.strokeStyle = ctx.fillStyle = window.logocolor;
    
    // Draw circle
    ctx.lineWidth = r / 6;
    ctx.beginPath();
    ctx.arc(cx, cy, r,  0, 2 * Math.PI);
    ctx.stroke();
    
    // Draw ticks
    var thickness = 0.05;
    draw_cone_fill(ctx, cx, cy, 0.0-thickness, 0.0+thickness, r * 0.6, r * 0.8);
    draw_cone_fill(ctx, cx, cy, 0.5-thickness, 0.5+thickness, r * 0.6, r * 0.8);
    draw_cone_fill(ctx, cx, cy, 1.0-thickness, 1.0+thickness, r * 0.6, r * 0.8);
    draw_cone_fill(ctx, cx, cy, 1.5-thickness, 1.5+thickness, r * 0.6, r * 0.8);
    
    // Draw a hashtag
    ctx.beginPath();
    var halfheight = r / 3;
    var halfwidth = 0.9 * halfheight;
    var skew = r / 30;
    var dist = halfheight / 3;
    //
    ctx.moveTo(cx - skew - dist, cy + halfheight);
    ctx.lineTo(cx + skew - dist, cy - halfheight);
    ctx.moveTo(cx - skew + dist, cy + halfheight);
    ctx.lineTo(cx + skew + dist, cy - halfheight);
    //
    ctx.moveTo(cx - halfwidth, cy - dist);
    ctx.lineTo(cx + halfwidth, cy - dist);
    ctx.moveTo(cx - halfwidth, cy + dist);
    ctx.lineTo(cx + halfwidth, cy + dist);
    //
    ctx.lineWidth = r / 20;
    ctx.stroke();
    
    var el = document.getElementById('canvasdownload');
    el.href = this.node.toDataURL(".png");
};


</script>

<input id='whitecheck' type='checkbox' />
<span id='colorlabel'>white</span>
<input id='sizerange' type='range' min='16' max='512' value='128' step='16' />
<span id='sizelabel'>16x16</span>
<a id='canvasdownload' href='#'>download</a>
<br />
<canvas id='canvas'>This website needs a working (HTML5) canvas.</canvas>
