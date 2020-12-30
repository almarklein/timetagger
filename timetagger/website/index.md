% TimeTagger - Tag your time, get the insight
% An open source time tracker that feels lightweight and has powerful reporting.

<style>
.panel {
    margin: 0;
}
.panel.wide {
    box-sizing: border-box;
    position: relative;
    text-align: center;
    width: 100vw;
    left: -1em;
    padding: 2em 4px;
}
@media screen and (min-width: 800px) { .panel.wide {
    left: calc(400px - 1em - 50vw);
}}
.panel.gray {
    background: #fcfcfc;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.2);
}
.panel.blue {
    background: rgba(208,229,253,1);
}

.panel > h2 {
    margin-top: 1em;
    margin-bottom: 1em;
    text-align: center;
    font-weight: bold;
    font-size: 200%;
}
.panel.blue > h2 {
    color: #fff;
}
</style>



<!-- ------------------------------ HERO ------------------------------ -->

<style>
.panel.hero {
    margin-top: -1em;
    padding-top: 50px;
    color: #000;
    text-align: center;
}
.panel.hero > img {
    float: right;
    max-width: 45%;
    max-height: 500px;
    display: none;
}
.panel.hero > div {
    text-align: left;
    padding-left: 2em;
    max-width: 550px;
}
@media screen and (min-width: 600px) { .panel.hero > img {
    display: block;
}}

@media screen and (min-width: 1000px) { .panel.hero > div {
    position: relative;
    left: calc(50vw - 500px);
}}
.hero h1 {
    font-family: "Ubuntu", Verdana, sans-serif;
    display: inline;
    font-size: 275%;
    color: #000;
}
h2 {
    color: #000;
}
.hero p {
    font-family: "Ubuntu", Verdana, sans-serif;
    color: #444;
    font-size: 130%;
}
.hero p .fas{
    display: inline-block;
    width: 1.8em;
    color: #B48B1C;
}
</style>

<div class='panel wide hero' style='padding-bottom: 0; margin-bottom: -300px;' >

    <img src='undraw_time_management_30iu_tt.svg' />

    <div>
        <h1>Tag your time<br>and see where it has gone</h1>
        <br /><br />

        <p>
        <br />
        An open source time-tracker that feels lightweight and has powerful reporting.
        </p>
        <br/>

        <a href='/signup' class='ctabutton'>
            <i class='fas'></i>&nbsp;&nbsp;Sign up</a>
        <a href='/demo' class='ctabutton demobutton'>
            <i class='fas'>\uf04b</i>&nbsp;&nbsp;Live demo</a>
        <br/>

        Try for free.
    </div>

    <div style='height: 380px; clear:both;'></div>

</div>


<!-- ------------------------------ Screenshots ------------------------------ -->

<style>
.looklikemonitor, .looklikephone {
    display: inline-block;
    position: relative;
    vertical-align: top;
}
.looklikemonitor { margin-left: 2vw; margin-right: -1em; }
.looklikephone { margin-right: 2vw; margin-left: -1em; }
@media screen and (min-width: 900px) { .looklikemonitor, .looklikephone {
    vertical-align: middle;
    margin-left: 30px;
    margin-right: 30px;
}}
.looklikemonitor > .images {
    position: relative;
    width: 60vw;
    height: 45vw;
    max-width: 600px;
    max-height: 450px;
}
.looklikephone > .images {
    position: relative;
    width: 10vw;
    height: 20vw;
    max-width: 100px;
    max-height: 200px;
}
.looklikemonitor > .images > img, .looklikephone > .images > img {
    position: absolute;
    left: 0; top: 0; width: 100%; height: 100%;
    transition: opacity 0.3s ease-in-out;
}
.looklikemonitor > .images, .looklikephone > .images, .looklikemonitor > span, .looklikephone > span  {
    display: block;
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    background-color: #222;
    border: 24px solid #222;
    border-radius: 24px;
}
.looklikemonitor > span {
    position: absolute;
    box-sizing: border-box;
    width: 100px;
    left: calc(50% - 50px);
    border-radius: 8px;
    margin-top: -9px;
}
.looklikephone > .images {
    border-width: 8px;
    border-radius: 4px;
}
.looklikephone > span {
    position: absolute;
    box-sizing: border-box;
    border-width: 8px;
    border-radius: 4px;
    width: 100%;
    margin-top: -5px;
}
.looklikemonitor a {
    position: absolute;
    left: -65px;
    font-family: "Ubuntu Condensed", "Ubuntu", Verdana, sans-serif;
    user-select: none;
    -moz-user-select: none;
    cursor: pointer;
    background: #fff;
    box-shadow: 0 4px 8px rgba(0,0,0,0.4);
    border-radius: 8px;
    padding: 0.5em;
    text-decoration: none;
    text-align: center;
    font-size: 25px;
}
.looklikemonitor a:hover {
    background: #f5f5f5;
    color: #000;
}
</style>

<script>
var _current_screenshot = -1;
function screenshotzoom(direction) {
    var container1 = document.getElementById('screenshots_desktop');
    var container2 = document.getElementById('screenshots_mobile');
    _current_screenshot += 1;
    if (_current_screenshot >= container1.children.length) {
        _current_screenshot = 0;
    } else if (_current_screenshot < 0) {
        _current_screenshot = 0;
    }
    for (var i=0; i<container1.children.length; i++ ) {
        var alpha = i <= _current_screenshot ? 1 : 0
        container1.children[i].style.opacity = alpha;
        container2.children[i].style.opacity = alpha;
    }
    var but = document.getElementById('screenshottogglebutton');
    but.innerHTML = "<i class='fas'>\uf302</i>&nbsp;&nbsp;" + (_current_screenshot + 1) + " / " + container1.children.length;
}
window.addEventListener('load', screenshotzoom)
</script>

<div class='panel wide'>

    <div class='looklikephone'>
        <div id='screenshots_mobile' class='images'>
            <img src='/screenshot11.png' />
            <img src='/screenshot12.png' style='opacity:0;'/>
            <img src='/screenshot13.png' style='opacity:0;'/>
        </div>
        <span></span>
    </div>

    <div class='looklikemonitor'>
        <div id='screenshots_desktop' class='images'>
            <img src='/screenshot1.png' />
            <img src='/screenshot2.png' style='opacity:0;'/>
            <img src='/screenshot3.png' style='opacity:0;'/>
        </div>
        <a id='screenshottogglebutton' onclick='screenshotzoom(+1);' style='bottom: 30px;'>
            <i class='fas'>\uf302</i>
        </a>
        <span></span>
    </div>

    <br /><br /><br /><br /><br />
</div>



<!-- ------------------------------ Key Features ------------------------------ -->

<style>
.features {
    color: #444;
    font-size: 110%;
    text-align: left;
    padding: 0 1em;
}

.features > img {
    display: block;
    max-height: 125px;
    margin-top: 3em;
    width: auto;
}
.features h3 {
    font-family: "Ubuntu Condensed", "Ubuntu", Verdana, sans-serif;
    color: #2399DA;
    font-size: 175%;
}

@media screen and (min-width: 500px) {
    .features {
        margin: auto;
        display: grid;
        grid-template-columns: 1fr 2fr;
        grid-gap: 1em 2em;
        justify-items: stretch;
        align-items: start;
    }
}
@media screen and (min-width: 840px) {
    .features > img {
        max-height: 175px;
    }
    .features {
        width: 800px;
        grid-template-columns: 1fr 1fr;
    }
}
@media screen and (min-width: 1024px) { .features {
        width: 1000px;
}}
</style>

<div class='panel wide gray'>

    <h2>Key features</h2>

    <div class='features'>


        <img src='undraw_celebration_0jvk_tt.svg' />
        <div>
            <h3>For anyone</h3>
            <p>
            Join the entrepreneurs, freelancers, artists, and others who
            use Time Turtle to track their time.
            </p>
        </div>

        <img src='undraw_Mobile_app_p3ts_tt.svg' />

        <div>
            <h3>Intuitive</h3>
            <p>
            We build TimeTurtle with the central idea that time is continuous.
            The result is an app that feels natural, giving you optimal control
            with a clean intuitive interface.
            </p>
        </div>

        <img src='undraw_dashboard_nklg_tt.svg' />

        <div>
            <h3>Overview & insight</h3>
            <p>
            You can smoothly navigate your timeline, move to past days and
            weeks, or zoom out to get a birds-eye view. This unique interactive
            experience results in a true sense of overview.
            </p>
        </div>

        <img src='undraw_files1_9ool_tt.svg' />

        <div>
            <h3>Powerful reporting</h3>
            <p>
            Hit the report button to get a detailed overview.
            Produce PDF reports to bill clients.
            Export data to a spreadsheet for further processing.
            </p>
        </div>

        <img src='undraw_off_road_9oae_tt.svg' />

        <div>
            <h3>Take it anywhere</h3>
            <p>
            TimeTurtle gives you the same great experience on any device, and
            is available as a web app, <a href='/support#faq-search=mobile'>mobile app</a>,
            and <a href='/support#faq-search=desktop'>desktop app</a>.
            It can be used off-line, and your data gets automatically synced.
            </p>
        </div>

        <img src='undraw_confirmed_81ex_tt.svg' />

        <div>
            <h3>Own your data</h3>
            <p>
            We make sure that your data is secure and backed-up. But you
            still own your data. You can always export all records for
            processing or to move it somewhere else.
            Note that you can also import your previous time tracking data from a CSV file.
            </p>
        </div>

        <img src='undraw_fingerprint_swrc_tt.svg' />

        <div>
            <h3>Privacy first</h3>
            <p>
            Notice how there's no cookie banner on this site? That's because we
            don't track you. Nor do we make use of 3d party services that do.
            Check our <a href='privacy'>privacy policy</a> for details.
            </p>
        </div>

    </div>

    <br /><br />

</div>


<!-- ------------------------------ Pricing ------------------------------ -->

<script>
function show_price_per_month(per_month) {
    var pro_node = document.getElementById('proplanprice');
    var buttons = document.getElementsByClassName('priceperiod');
    if (per_month) {
        pro_node.innerHTML = "<b>$4 per month</b><br> billed monthly";
        for (var but of buttons) {
            if (but.innerText.indexOf("month") >= 0) {but.classList.add('active');
            } else {but.classList.remove('active')}
        }
    } else {
        pro_node.innerHTML = "<b>$3 per month</b><br> billed annually";
        for (var but of buttons) {
            if (but.innerText.indexOf("year") >= 0) {but.classList.add('active');
            } else {but.classList.remove('active')}
        }
    }
}
window.addEventListener('load', function() {show_price_per_month(false);})
</script>
<style>
a.priceperiod {
    display: inline-block;
    user-select: none;
    -moz-user-select: none;
    background: #FEDFAB;
    border: 1px solid #B48B1C;
    color: #000;
    border-radius: 10px;
    padding: 0.2em 0.5em;
    cursor: pointer;
}
a.priceperiod i.fas {
    color: #ccc;
}
a.priceperiod.active i.fas {
    color: #000;
}
a.priceperiod:hover {
    color: #000;
    text-decoration: none;
    color: #765A0F;
}

</style>

<div class='panel'>

    <h2>Pricing</h2>

    <br />

    <div class='pricing-container wider'>

        <a class='pricing-box' href='#' onclick='auth.signup("/app")'>
            <h3> Starter </h3>

            <span class='price'><b>Always free</b><br>&nbsp;</span>
            <br><hr>

            <br><i class='fas'>\uf00c</i> All features shown below
            <br><i class='fas'>\uf00c</i> Create up to 5 projects
            <br><br><br><br><br>

            <hr>
            <span class='action'><i class='fas'></i> Sign up</span>
        </a>

        <a class='pricing-box' href='#' onclick='auth.signup("/account")'>
            <h3> Pro </h3>

            <span id='proplanprice' class='price'><b>$3 per month</b><br></span>
            <br><hr>

            <br><i class='fas'>\uf00c</i> All features shown below
            <br><i class='fas'>\uf00c</i> Unlimited projects
            <br><i class='fas'>\uf00c</i> Priority support
            <br><br><br><br>

            <hr>
            <span class='action'><i class='fas'></i> Sign up</span>
        </a>

        <a class='pricing-box' href='/support'>
            <h3> Enterprise </h3>

            <span class='price'><b>Custom pricing</b><br>starting at 25 users</span>
            <br><hr>

            <br><i class='fas'>\uf00c</i> Everything in Pro
            <br><i class='fas'>\uf00c</i> Management reports
            <br><i class='fas'>\uf00c</i> Customizable solutions
            <br><i class='fas'>\uf00c</i> Hosted or on premise
            <br><br><br>

            <hr>
            <span class='action'><i class='fas'>\uf1fa</i> Contact us</span>
        </a>

    </div>

    <br />

    <p style='text-align:center;'>
        The Pro plan's reference price is in US Dollars, but in most countries you pay in your local currency.
    </p><p style='text-align:center;'>
        <i class='fas'>\uf059</i>&nbsp; See the <a href='/support#purchase'>support page</a> for information about payments, VAT, and more.
    </p>

    <br />

</div>


<!-- ------------------------------ All Features ------------------------------ -->

<style>
.panel.allfeatures .fas {
    color: #B48B1C;
}
</style>

<div class='panel allfeatures'>

    <h2>Features available in all plans</h2>

    <i class='fas'>\uf1ae</i>&nbsp;&nbsp; An intuitive time tracking experience.
    <br /><br />
    <i class='fas'>\uf3cd</i>&nbsp;&nbsp; Works on all modern browsers, also on smartphones and tablets.
    <br /><br />
    <i class='fas'>\uf2f1</i>&nbsp;&nbsp; Automatic syncing between devices.
    <br /><br />
    <i class='fas'>\uf072</i>&nbsp;&nbsp; Can be used off-line (e.g. during traveling or on remote locations).
    <br /><br />
    <i class='fas'>\uf1c1</i>&nbsp;&nbsp; Export reports as PDF.
    <br /><br />
    <i class='fas'>\uf0ce</i>&nbsp;&nbsp; Export reports to spreadsheets.
    <br /><br />
    <i class='fas'>\uf56f</i>&nbsp;&nbsp; Import time record data from e.g. CSV.
    <br /><br />
    <i class='fas'>\uf023</i>&nbsp;&nbsp; All communication is SSL encrypted.
    <br /><br />
    <i class='fas'>\uf0c7</i>&nbsp;&nbsp; Your data is backed up multiple times in case something goes wrong.
    <br /><br /><br />

</div>
