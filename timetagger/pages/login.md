# Login

<script src='./app/tools.js'></script>

<script>
async function login(path) {

    let el = document.getElementById("result");
    el.innerHTML = "Logging in ..."
    await tools.sleepms(100);

    let url = tools.build_api_url(path);
    let init = {method: "GET", headers:{}};
    let res = await fetch(url, init);
    if (res.status != 200) {
        let text = await res.text();
        el.innerText = "Could not get token: " + text;
        el.innerHTML = el.innerHTML + "<br><a href='../'>TimeTagger home</a>";
        return;
    }

    let token = JSON.parse(await res.text()).token;
    tools.set_auth_info_from_token(token);
    el.innerText = "Token exchange succesful";

    let state = tools.url2dict(location.hash);
    location.replace(state.page || "./app/");
}

async function login_localhost() {
    await login("webtoken_for_localhost");
}

async function login_credentials() {
    let input_u = document.getElementById("input_u");
    let input_p = document.getElementById("input_p");
    let params = "username=" + input_u.value + "&pw=" + input_p.value;
    await login("webtoken_for_credentials" + "?" + params);
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
}

window.addEventListener('load', load);
</script>

<input id='input_u' type='text' placeholder='username' style='margin:4px;'/><br />
<input id='input_p' type='password' placeholder='password' style='margin:4px;'/><br />
<button id='submit_up' class='whitebutton' style='margin:4px;' >Submit</button>

<br />
<button id='submit_localhost' class='whitebutton' style='margin:4px; display: none;' >Login as default user (on localhost)</button>

<p id='result'></p>
