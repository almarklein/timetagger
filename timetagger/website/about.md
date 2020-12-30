% TimeTagger- About
% Who builds TimeTagger, and what tech do we use.

<img style='max-height:200px; float:right' src='undraw_time_management_30iu_tt.svg' />

# About TimeTagger


## company | Company

TimeTagger is a product by [Canpute](https://canpute.com), located in the Netherlands, registered at
the chamber of commerce under 61855448.


## oss | Open source

We ♥ open source! Some projects that have spun out of TimeTagger:

* [Asgineer](https://github.com/almarklein/asgineer)
* [MyPaas](https://github.com/almarklein/mypaas)
* [ItemDB](https://github.com/almarklein/itemdb)
* [fastuaparser](https://github.com/almarklein/fastuaparser)

By subscribing to TimeTagger you are supporting open source software.


## tech | Technology

If you're interested, this is how we build TimeTagger:

### Front-end

The TimeTagger app is for the most part implemented in Python and
compiled to JavaScript using [PScript](https://pscript.readthedocs.io).
The drawing is all done using the HTML5 canvas API (no WebGL). A
specially designed binary heap is used to query records and aggregations
(i.e. summaries over a period of time) fast enough to realize
real-time interaction no matter at what time-scale you view your data. We
do not make use of third party JS libraries (except for PDF generation)
and are proud to not use NPM :)

### Back-end

The TimeTagger backend runs on servers provided by [Upcloud](https://upcloud.com/),
in a datacenter in Amsterdam. The VM runs Ubuntu Linux; we use
[Docker](https://en.wikipedia.org/wiki/Docker_(software)) to create a
consistent environment between testing and deployment. [Traefik](https://traefik.io)
is used as a load balancer and reverse proxy. Both are managed by
[MyPaas](https://github.com/almarklein/mypaas), which also handles
deployments. The server software is implemented in
[Python](https://python.org), using the lightning-fast
[Uvicorn](https://www.uvicorn.org/) ASGI server with
[Asgineer](https://asgineer.readthedocs.io) on top.
