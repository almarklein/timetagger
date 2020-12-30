% TimeTagger - Support
% Support, knowledge base, FAQ.

<script src='/faq-div.js'></script>

<style>
.faq h2 {
    color: #333;
}
</style>

<img style='max-height:200px; float:right' src='undraw_questions_75e0_tt.svg' />

# TimeTagger Support

Type your question in the box below. The answer might be in the FAQs.
If not, see GH.

TODO needs work


<div class='faq-this-start' data-email='timeturtle@canpute.com'></div>

<br />

## general | General


### Why should I track my time?

You don't have to. But tracking your time can be a great way to get more
insight into what you actually spend your time on. And then adjust to become
more efficient; it makes you much more aware of how your time is spent.

And some people simply need to know how much time they spend on certain tasks,
e.g. because those worked hours have to be billed to a client.


### How does TimeTurtle tack my time?

A time tracker should be as simple as possible. In TimeTurtle you start
and stop a timer by clicking the big play-button. Records can also be
added and edited later.


### How does TimeTurtle show my tracked time?

To check on your spent time, TimeTurtle offers a unique interactive
experience, based around a linear timeline. It's easy to navigate the
timeline using buttons, scrolling and swiping. All the time, the
overview panel shows useful statistics. E.g. by zooming out to a week,
month, or year, you directly see the corresponding statistics.



## supportedon | Running TimeTurtle on ...

### What browsers are supported?

Supported browsers include Firefox, Chrome, Safari, Edge, and their mobile counterparts.


### Does TimeTurtle work on mobile devices?

Yes, the TimeTurtle app is designed to work well on small screens.
Simply open it in your mobile webbrowser. If it does not work with your
standard browser, we recommend installing Firefox or Chrome.

TimeTurtle can also be installed as a native app on Android and iOS:
open the app (https://timeturtle.app<b>/app</b>) in your phone's browser, and
select "Add to homescreen". Some devices will show a prompt, in others you may
find the option in the menu.


### Is TimeTurtle available via Google Play / the Appstore?

No, but you can still install it: TimeTurtle is designed as a
Progressive Web App (PWA), which makes it possible to install it outside
of the playstore/appstore. Open the app
(https://timeturtle.app<b>/app</b>) in your phone's browser, and select
"Add to homescreen". Some devices will show a prompt, in others you may
find the option in the menu.

We may at some point add it to the official stores to make it easier
for users to discover and install TimeTurtle.


### Can TimeTurtle be run as a desktop app?

Yes. Open the app in the Chrome browser, and then click "Install
TimeTurtle App" (or similar) in the address bar.


### Can TimeTurtle be used off-line?

Yes, in any way you are using TimeTurtle (from a browser, mobile app, or desktop app),
the TimeTurtle app page will still work when there is no internet connection.

New records (and changes to existing records) are stored in
the browser/application cache. Therefore, when you don't have an internet
connection (e.g. while traveling), you can safely use TimeTurtle and let it sync
later. You can safely close the browser, but note that the local data is cleared
when you log out.



## purchase | Plans and billing


### Is TimeTurtle free?

Yes, you can <a href='/signup'>sign up</a> to get access to the Starter
plan, which is free forever, and gives you all the features, except that it
has a maximum for the number of projects that you can create.
You can then upgrade to Pro when you want.


### How can I purchase the Pro plan?

You must first sign up for an account. By default you are on the Starter plan.
You can then purchase the Pro plan via the [account page](/account).
We make use of [Paddle](https://paddle.com) to handle our purchases
with a simple and secure checkout experience.


### Do the prices include VAT?

Yes, all our prices include VAT. The amount of VAT depends on your
country and whether you represent a company. The VAT is calculated
automatically and will be shown on your invoice.


### Can I purchase the Pro plan if I don't have a creditcard?

The payment service allows payments with creditcard, Paypal and Apple Pay.
If you prefer to pay from your bank account, you can connect your bank account
with a Paypal account, and then pay via Paypal.


### Can I purchase a subscription from my business?

Yes, you can! During the checkout, you can enter your VAT number and
company details. You can also edit these details on the invoice that
you receive via email.


### What is the billing period?

You can choose to be billed monthly or yearly. Since the payment
processor overhead costs are high compared to our low prices, the costs
for a yearly plan are considerably lower.


### How can I cancel my Pro plan?

You can cancel your plan from the account page. This will bring you
back to the Starter plan. You keep all the projects that you currently have,
but will be unable to create new projects if you already have more than
the maximum of the Starter plan.



## bugsfeatures | Bugs and features


### What features can I expect in the (near) future?

We keep a public [issue board](https://gitlab.com/canpute/timeapp/boards), where
you can see the things that are on the roadmap. You can also let us know your
interests by voting on the issues corresponding to certain features
(you need a Gitlab account for that).


### How can I request a feature?

First check our [issue list](https://gitlab.com/canpute/timeapp/issues) whether
the issue has been requested already. If so, hit the thumbs-up sign to let us
know your interest (you need to be logged in with Gitlab for this).
Otherwise, create a new issue (if you have an account with Gitlab) or [contact us](/support).


### I think I discovered a bug, what should I do?

First check the [issue list](https://gitlab.com/canpute/timeapp/issues) whether
the bug is already known. If not, please create a new issue or [contact us](/support).



## app | The application



### How do I create groups and sub-projects?

In TimeTurtle, each project can be seen as a label. Projects are grouped
*implicitly* based on their name, using the forward slash (`"/"`). E.g. to
make a project `"admin"` a subproject of `"unpaid work"`, simply rename it
`"unpaid work/admin"`. The project `"unpaid work"` does not even have
to exist by itself.


### Can I merge two projects?

Yes, a project can be merged with another simply by giving it the same
name. The dialog will display a warning that a merge will take place.
In practice, a merge means that all time records associated with one
of the projects are updated to use the other, and the now unused project
is hidden. Try it out in de <a href='/demo'>demo</a>!


## importexport | Importing and exporting


### How can I import data?

TimeTurtle can import time records from Excel or CSV files, e.g.
to restore from your own backup, or to import time records from another
tracker.

In the app, click the menu button and select "import records". It is recommended
to first import your data in the <a target="new" href="/sandbox">sandbox</a>
so you can check that the import has the expected result.

Importing should just work for time records exported by Yast, and
possibly other trackers too. If you have trouble getting the import to
work, open your data in a spreadsheet (e.g. Excel, Libre Office, Google
sheets) and see if it might need a change in the header names, or
perhaps a small conversion.

Below you'll find the technical details on what TimeTurtle expects for imported data.
Feel free to [send](/support) an (anonymised) sample, so
we can add support for your data or help you convert it.


### How should my import-data be formatted?

The import data should consist of rows, where each row represents one
record, and the top row is the header. Values on a row can be separated
with either tab, comma, or semicolon (this is automatically detected).
Wrapping values in double-quotes (as is common in CSV files) is
supported.

The supported headers are listed below. Common aliases for each field
are automatically converted. Each record should be resolvable into
at least a project, a start time and a stop time.
<ul>
<li><b>key:</b> existing records are replaced if they match the given key/id. If no key is provided, existing
records are replaced if the start/stop times match.</li>
<li><b>project:</b> the name of the project associated with the record.</li>
<li><b>start time:</b> a Unix timestamp or other date-time string (e.g. ISO 8601).</li>
<li><b>stop time:</b> a Unix timestamp or other date-time string (e.g. ISO 8601).</li>
<li><b>description:</b> the description/comment. Newlines and tabs are removed.</li>
</ul>

Additional headers are supported to deal with exports of other trackers:
<ul>
<li><b>date:</b> if given, the start time can also be in `hh:mm` or `hh:mm:ss` format.</li>
<li><b>duration:</b> can be `hh:mm`, `hh:mm:ss`, or simply the number of seconds. Is used when the stop time is not of the preferred format.</li>
</ul>


### How can I export my data?

TimeTurtle has two export mechanisms: the report and the full export.

The report dialog (which opens via the report button on the
left) produces a table that can be saved as PDF or copied into a spreadsheet.
The latter can be convenient if you want to process data of a
certain project and/or time period. It can also represent durations
in decimal hours, which is usually easier to process in a spreadsheet.

The full export dialog (which opens via the menu) produces a table that
contains the data of all your records. The table can be copied into a
text file or a spreadsheet, and has the following columns: key, project,
start, stop, description. The output of a full export gives you access
to your "raw" data, and can e.g. be used in the import dialog.


<div class='faq-this-end'></div>
