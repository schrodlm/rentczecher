Photos were next on the list when one question stopped everything: would releasing rentczecher get me into legal trouble? I spent two days finding out, and then cleaning up the repository wherever it was less careful than it should be.

I am not a lawyer, and this is not legal advice. It is what I learned and what I decided.

## The question that matters

Scraping real-estate portals touches several areas of law, but in the EU the central one is the database right. It protects the investment someone made in building a database, and whether a tool infringes it depends a lot on whether the tool harms that investment.

A tool that serves one person, runs on their own computer and sends them back to the portal for every listing is about as far from that as a scraper can be. The cases I found were all about companies running one service for the public and republishing listings and photos. What protects a tool is its shape, not its intentions.

## Staying small on purpose

So I decided to keep rentczecher in that shape on purpose. There is no hosted version and nothing is shared between users. There is no paid tier. Every listing links back to the portal it came from, and rentczecher never republishes anything. The README now says this plainly, and says that a portal operator with a concern gets a quick answer.

Sreality's terms for visitors forbid automated access. So Sreality, and Bezrealitky too, will be off by default. You turn them on yourself in a profile after seeing what each portal asks.

## Crediting the data

The place data comes from RÚIAN, published by ČÚZK under CC BY. I had treated it simply as free data, but CC BY comes with homework: a visible credit, a link to the licence and a note on what was changed. The map in the app now shows the credit, and the README describes what was modified.

The tests had a similar problem. Some recorded Sreality responses used as test fixtures were real people's adverts. I replaced them with made-up listings of the same shape.

## A licence

rentczecher is now licensed GPL-3.0-or-later, across the engine, the panel and the desktop shell. Anyone may use it, change it and share it, but whoever passes it on has to pass on the source under the same licence. I chose GPL over a permissive licence so that rentczecher and any fork of it stay free. The name and the logo are not part of the licence.

The panel's build now also lists the licences of every package it ships, the first step towards the notices the installers will carry.
