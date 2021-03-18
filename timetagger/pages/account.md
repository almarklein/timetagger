% TimeTagger - Account
% User account

# Account

<!--account_start-->

<script src='./app/tools.js'></script>

<script>

function nav_to(url) {
    location.href = url;
}

async function refresh_auth_status() {
    let el = document.getElementById('authstatus');
    let logoutallbutton = document.getElementById('logoutallbutton');

    el.innerHTML = "Getting auth status ...";
    await tools.sleepms(200);

    let auth = tools.get_auth_info();

    if (auth) {
        let html = "Logged in as <b>" + auth.username + "</b>";
        //html += "<br>Web token valid until ";
        //html += new window.Date(auth.exp * 1000).toISOString().split("T")[0];
        //html += " (will be auto-renewed)";
        el.innerHTML = html;
        logoutallbutton.disabled = false;
    } else {
        el.innerHTML = "Not logged in.";
        logoutallbutton.disabled = true;
    }
}

async function refresh_api_token(reset) {
    let el = document.getElementById('apitoken');
    let resetapikeybutton = document.getElementById('resetapikey');
    let auth = tools.get_auth_info();

    el.innerHTML = "Getting Getting API token ...";
    await tools.sleepms(200);

    if (auth) {
        let url = tools.build_api_url("apitoken");
        if (reset) { url += "?reset=1"; }
        let init = {method: "GET", headers:{authtoken: auth.token}};
        let res = await fetch(url, init);
        if (res.status != 200) {
            el.innerText = "Fail: " + await res.text();
            return;
        }
        d = JSON.parse(await res.text());
        el.innerText = d.token;
        resetapikeybutton.disabled = false;
    } else {
        el.innerHTML = "Not available.";
        resetapikeybutton.disabled = true;
    }
}

async function reset_webtoken_seed() {
    let el = document.getElementById('logoutallbutton');
    el.innerHTML = "Resetting web token seed ...";
    await tools.renew_webtoken(true, true);
    await tools.sleepms(1000);
    el.innerHTML = "Done!";
    await tools.sleepms(1000);
    el.innerHTML = "Logout all other devices";
}

async function reset_api_key() {
    await refresh_api_token(true);
}

async function copy_api_key() {
    let el = document.getElementById('apitoken');
    let but = document.getElementById('copyapikey');
    tools.copy_dom_node(el)
    but.innerHTML = "<i class='fas'></i>";
    await tools.sleepms(1000)
    but.innerHTML = "<i class='fas'></i>";
}

var refresh_functions = [refresh_auth_status, refresh_api_token];
function refresh() {
    for (let func of refresh_functions) {
        func();
    }
}
window.addEventListener("load", refresh);
</script>

<style>
#apitoken {
    overflow-wrap: anywhere;
    margin-left: 5px;
    font-size:80%;
}
</style>

<br />

<button onclick='window.refresh()' style='float: right;' class='whitebutton'><i class='fas'>\uf2f1</i> Refresh</button>

## Authentication status

<div id='authstatus'>Getting auth status ...</div>

<button class='whitebutton' onclick='nav_to("./login#page=./account");'>Log in</button>
<button class='whitebutton' onclick='nav_to("./logout#page=./account");'>Log out</button>
<button class='whitebutton' id='logoutallbutton' disbaled onclick='reset_webtoken_seed();'>Logout all other devices</button>

<details style='font-size: 80%; padding:0.5em; border: 1px solid #ddd; border-radius:4px;'>
    <summary style='user-select:none;'>web-token details</summary>
    <p>
    Authentication occurs using a web-token that is obtained when logging in.
    The token is valid for 14 days, and is refreshed when you use the application.
    It is recommended to log out on devices that you do not own. In case you forget,
    or when a device is lost/stolen, the token seed can be reset, causing all other sessions to log out.
    </p>
</details>
<br />

## API token

<div id='apitoken' class='monospace'>Getting API token ...</div>

<button type='button' class='whitebutton' id='resetapikey' onclick='reset_api_key();'>Reset API token</button>
<button type='button' class='whitebutton' id='copyapikey' onclick='copy_api_key();'><i class='fas'></i></button>

<details style='font-size: 80%; padding:0.5em; border: 1px solid #ddd; border-radius:4px;'>
    <summary style='user-select:none;'>api-token details</summary>
    <p>
    The API token enables access to the server for 3d party applications (e.g. the CLI tool). API tokens do not expire.
    Reset the token to revoke access for all applications using the current API token.
    </p>
</details>
<br />

<!--account_end-->
