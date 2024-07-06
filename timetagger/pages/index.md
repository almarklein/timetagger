<script src='./app/tools.js'></script>

<script>
let state = tools.url2dict(location.hash);
location.replace(state.page || "./login");
</script>
% TimeTagger - Tag your time, get the insight
% An open source time tracker that feels lightweight and has powerful reporting.

<br />

<img src='timetagger_wd.svg' width='350px' />
<h1 class='normalfont'><span style='border-bottom: 3px solid #DEAA22;'>Tag</span> your time,<br>get the <span style='border-bottom: 3px solid  #DEAA22;'>insight</span>.</h1>

<style>
main a.ctabutton {
    display: inline-block;
    border: none;
    border-radius: 4px;
    background: #fff;
    padding: 1em;
    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.4);
    transition: box-shadow 0.1s;
    font-size: 120%;
    margin: 0.5em;
}
main a.ctabutton:hover {
    text-decoration: none;
    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.4);
}
</style>

<div>
    <a href='app/demo' class='ctabutton'>
        <i class='fas'>\uf04b</i>&nbsp;&nbsp;Demo</a>
    <a href='app/' class='ctabutton'>
        <i class='fas'>\uf04b</i>&nbsp;&nbsp;App</a>
</div>

----

This is the stub index page for TimeTagger,
an open source time-tracker that feels lightweight and has powerful reporting.

Links:

* [Main website](https://timetagger.app)
* [Source code on Github](https://github.com/almarklein/timetagger)
* [Docs on RTD](https://timetagger.readthedocs.io)
* [CLI tool](https://github.com/almarklein/timetagger_cli)
