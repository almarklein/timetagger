# Login

<script src='./app/tools.js'></script>

<script>
async function login(payload, silent) {

    // Reset status
    let el = document.getElementById("result");
    if (!silent) {
        el.innerHTML = "Logging in ..."
    }
    await tools.sleepms(100);

    // The body is obfuscated with base64, but not encrypted.
    let body = btoa(JSON.stringify(payload));

    // Do request
    let url = tools.build_api_url("bootstrap_authentication");
    let init = {method: "POST", headers: {}, body: body};
    let res = await fetch(url, init);

    // Handle response
    if (res.status != 200) {
        if (!silent) {
            let text = await res.text();
            el.innerText = "Could not get token: " + text;
            el.innerHTML = el.innerHTML + "<br><a href='../'>TimeTagger home</a>";
        }
    } else {
        let token = JSON.parse(await res.text()).token;
        tools.set_auth_info_from_token(token);
        el.innerText = "Token exchange succesful";
        let state = tools.url2dict(location.hash);
        location.replace(state.page || "./app/");
    }
}

async function login_localhost() {
    await login({"method": "localhost"});
}

async function login_credentials() {
    let input_u = document.getElementById("input_u");
    let input_p = document.getElementById("input_p");
    await login({"method": "usernamepassword", "username": input_u.value, "password": input_p.value});
}

async function load() {
    let but1 = document.getElementById("submit_up");
    let but2 = document.getElementById("submit_localhost");
    let input_p = document.getElementById("input_p");

    but1.onclick = login_credentials;
    but2.onclick = login_localhost;
    input_p.onkeydown = function (e) { if (e.key == "Enter" || e.key == "Return") {login_credentials();} };

    if (location.hostname == "localhost" || location.hostname == "127.0.0.1") {
        but2.style.display = "block";
    }

    // Try to autheticate through a reverse proxy but ignore the unsuccessful result
    await login({"method": "proxy"}, true);
}

window.addEventListener('load', load);
</script>

<input id='input_u' type='text' placeholder='username' style='margin:4px;'/><br />
<input id='input_p' type='password' placeholder='password' style='margin:4px;'/><br />
<button id='submit_up' class='whitebutton' style='margin:4px;' >Submit</button>

<br />
<button id='submit_localhost' class='whitebutton' style='margin:4px; display: none;' >Login as default user (on localhost)</button>

<p id='result'></p>
