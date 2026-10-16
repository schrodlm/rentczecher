rentczecher now has a website at rentczecher.cz and a README you can read in two minutes. Until now the README was one long page of everything, from the command line to the place data's licence. Now it is a short introduction, and the technical detail lives on pages of its own.

## The website

The site is a static SvelteKit build in Czech and English, published from the repository by GitHub Pages. It explains what the app does, shows it in screenshots, has a roadmap, this devlog, and a page for portal operators who find rentczecher's User-Agent in their logs. The screenshots come from the app's test scenarios, which are made-up listings, so no real advert ever appears on the site.

## A README for people who want to use it

The README starts with the logo, a few badges for the build and the release, and a screenshot of the inbox that follows your light or dark theme. Then it says what the app does, how to download it, how it uses the portals, and where to start if you want to help.

The idea the whole app is built around got its own section: the profile. A profile is one of your searches, saved and watched for you. It has criteria, which decide what shows up at all, portals, which are the sites it asks, and preferences, which only decide the order.

There is also a diagram of the app's three parts, the shell, the panel and the engine, and how they talk to each other. It is written in Mermaid, a small language for diagrams that GitHub draws on the page, so it follows the reader's theme and never needs a new picture. I coloured it with the app's own palette.

The README names no portal. The portals are listed in one table on a separate page, so adding one changes a single row.

## Pages for the technical side

Everything else moved to its own page: a contributing guide, an overview of the architecture, an architecture page for each of the three parts, and pages on running the engine without the app, building it, troubleshooting and the place data's credit. I kept the architecture pages high level, saying what each part does and why, rather than listing every type in the code.

Before writing anything I checked every claim in the old README against the code. It still called the app a cron script, said scores were not shown yet, and promised to keep listings forever. None of that was true anymore.

## Saying only what is true

I did the same for the website. The page for portal operators promised a cap on how many pages a search reads, a minimum time between scans and backing off after a refusal, and none of those existed yet. It now says only what the app does, and each promise goes back once the code is there. The site also stopped naming the next portal before I have checked what that portal asks, stopped claiming scans run on a schedule, and explains the Windows warning next to the macOS one.

## Credit on every map

The place data comes from RÚIAN under CC BY 4.0, which asks every view of the data to credit ČÚZK, link the licence and say what was changed. Only the large map in the profile editor did that. Now every map does, the small ones too, with a link to the licence and a note that the outlines are traced from the places' centres.
