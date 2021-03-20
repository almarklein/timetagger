# Login

<script src='./app/tools.js'></script>

<script>
async function login() {

    let el = document.getElementById("result");

    let url = tools.build_api_url("webtoken_for_localhost");
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

window.addEventListener('load', login);
</script>

Logging in ...

<p id='result'></p>
