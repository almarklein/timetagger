# Logout

<script src='./app/tools.js'></script>

<script>

async function logout() {
    await tools.logout();

    let state = tools.url2dict(location.hash);
    location.replace(state.page || "./");
}

window.addEventListener('load', logout);
</script>

Logging out ...
