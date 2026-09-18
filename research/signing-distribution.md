# Signing and distribution decision sheet — Tauri v2 desktop app

Retrieved 2026-09-18. Prices and platform policies drift; re-verify before acting on this if it's more than a few months old, especially the Azure Trusted Signing / Artifact Signing eligibility rules, which have already changed twice in two years.

Scope: a free, open-source Tauri v2 desktop app (Windows + macOS + Linux) built by a solo hobbyist maintainer with no budget for signing infrastructure.

## 1. Windows

### Certificate options and cost

Microsoft's own comparison ([Code signing options for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options), Microsoft Learn, updated 2026-08-29) lays out the current options for apps distributed outside the Microsoft Store:

| Option | Cost | Who can use it |
| --- | --- | --- |
| Azure Artifact Signing (formerly Trusted Signing) | ~$9.99/month (~$120/year) | Organizations: USA, Canada, EU, UK. **Individuals: USA and Canada only.** |
| OV certificate (DigiCert, Sectigo, etc.) | $150–300/year | Worldwide |
| EV certificate | $400+/year | Worldwide |
| Self-signed | Free | Blocks installation for public users — dev/test only |
| No signature | Free | Strong SmartScreen block; enterprises may block entirely |

**Azure Trusted Signing eligibility — this is the load-bearing fact and it is confirmed current as of today.** Microsoft's own quickstart ([Quickstart: Set up Artifact Signing](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart), Microsoft Learn, updated 2026-09-15 — three days old at time of writing) states plainly:

> "Public Trust certificates are available to organizations in the United States, Canada, the European Union, the United Kingdom, Australia, New Zealand, Japan, South Korea, Singapore, Switzerland, Norway, and Israel. **Individual developers must be located in the United States or Canada.** These geographic restrictions do not apply to Private Trust certificates."

Private Trust certificates aren't useful here — they aren't trusted by default Windows installs (they're for internal/enterprise CI policy signing), so they don't solve the SmartScreen problem for public distribution.

The earlier, much-discussed 2025 tightening (requiring a business with 3+ years of verifiable history) is **no longer the current rule** for individuals — Microsoft opened Trusted Signing to individual developers in public preview in October 2024 ([Trusted Signing is now open for individual developers to sign up in Public Preview!](https://techcommunity.microsoft.com/blog/microsoft-security-blog/trusted-signing-is-now-open-for-individual-developers-to-sign-up-in-public-previ/4273554), Microsoft Community Hub) — but individual eligibility is now gated by **country of residence**, not business history: US/Canada only. This is a geographic restriction, not a business-vintage restriction, and it does not appear to have relaxed since. The Microsoft Learn quickstart (dated three days before this research) confirms US/Canada-only for individuals is still current.

**Bottom line for a non-US/Canada solo hobbyist (e.g. based in Czechia): Azure Trusted Signing is not available as an individual.** The only paths to a trusted Windows certificate are an OV cert ($150–300/year, worldwide) or forming a qualifying business entity (not realistic for a zero-budget hobby project). One additional free option exists and is documented directly on the same Microsoft Learn page: **[SignPath Foundation](https://signpath.io) offers free OV-level code signing for qualifying open-source projects** via a managed CI pipeline — worth investigating as a zero-cost path, though eligibility/review criteria are SignPath's own and weren't independently verified here beyond Microsoft's pointer to it.

### What happens to an unsigned app in SmartScreen

This is **not a hard block** — it's a click-through warning, with one important exception. Per Microsoft's own [SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) (Microsoft Learn, updated 2026-08-17):

- Unsigned downloads show a "Windows protected your PC" SmartScreen prompt; the user must click "More info" then "Run anyway" before the app will run.
- Enterprise policy can disable the "Run anyway" bypass entirely, blocking unsigned apps outright on managed machines — this doesn't affect a typical home user but matters if the audience includes corporate devices.
- On Windows 11, a separate feature called **Smart App Control** can supersede SmartScreen and block unsigned files outright regardless of reputation, for devices where it's enabled.

**Reputation does build over time, but only meaningfully for signed files.** Verbatim from Microsoft: "When a file is not signed, SmartScreen reputation must build for each new version of your files, starting with zero reputation. Reputation cannot transfer from previous versions unless both were signed using the same publisher identity." In practice this means an *unsigned* app essentially never escapes the warning — every new release version starts back at zero reputation. A *signed* app (even a cheap OV cert) accumulates reputation tied to the certificate/publisher identity across versions, and the warning eventually stops appearing after "several weeks and hundreds of clean installs from a wide audience" (Microsoft's own estimate).

One more important, non-obvious fact confirmed directly from Microsoft's page: **EV certificates no longer bypass SmartScreen.** That special "instant trust" behavior for EV certs was removed in 2024; EV and OV now behave identically for SmartScreen purposes. Paying the EV premium ($400+/year vs ~$150–300/year for OV) buys nothing extra for this use case.

## 2. macOS

### Cost

The Apple Developer Program costs **$99/year**, confirmed directly from Apple's own pricing page ([Apple Developer Program](https://developer.apple.com/programs/)): "$99 annual membership." There is a free tier (Xcode beta access, on-device testing, forums) but it does **not** include the Developer ID certificate needed to sign/notarize apps for distribution outside the App Store — that requires the paid $99/year tier.

### What notarization requires

Per Apple's own documentation ([Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), developer.apple.com) and corroborated by Apple's Sequoia runtime-protection announcement, the process is:

1. Sign the app with a **Developer ID Application certificate** (requires the paid $99/year membership — a Developer ID cert is not available on the free tier).
2. Submit the signed app/archive to Apple's notary service via `notarytool` (the modern replacement for the deprecated `altool`), e.g. `xcrun notarytool submit path/to/app.zip --apple-id ... --team-id ...`. The notary service "automatically scans your Developer ID-signed software and performs security checks" and issues a notarization ticket.
3. **Staple** the ticket to the app with `xcrun stapler staple path/to/app.app`, so Gatekeeper can verify it offline without a network call at launch time.

Tauri automates steps 1–3 during its build process when given the right credentials as environment variables — this is a build-pipeline integration question, not a separate cost.

### Gatekeeper behavior on current macOS (post-Sequoia) — this is the part that trips people up

Apple's own Sequoia announcement ([Updates to runtime protection in macOS Sequoia](https://developer.apple.com/news/?id=saqachfa), developer.apple.com) states the exact change, verbatim:

> "In macOS Sequoia, users will no longer be able to Control-click to override Gatekeeper when opening software that isn't signed correctly or notarized. They'll need to visit System Settings > Privacy & Security to review security information for software before allowing it to run."

This is a **real UX regression for unsigned apps**, not a cosmetic change — the old "right-click → Open → confirm" bypass that worked from Catalina through Sonoma is gone as of Sequoia. The **current, accurate recovery path**, per Apple's own support article ([Safely open apps on your Mac](https://support.apple.com/en-us/102445), support.apple.com):

1. The user double-clicks the app; macOS refuses to open it and shows a warning (for a genuinely unsigned/tampered app this can appear as "app is damaged and can't be opened," which reads to a lay user as if the download is corrupted, not that it's merely unsigned — a significant trust/support-burden problem for a hobby project).
2. The user opens **System Settings → Privacy & Security**, scrolls down, and clicks **Open Anyway** next to the blocked app's entry.
3. The warning reappears; the user clicks **Open** to confirm, and authenticates as an administrator if prompted.
4. The app is then saved as an exception and opens normally on future launches (Apple: "The app is now saved as an exception to your security settings, and you can open it in the future by double-clicking it.")

So: **not a hard block**, but it requires the user to leave the warning dialog, navigate System Settings, and take a deliberate multi-step action within roughly an hour of the first blocked attempt (per widely corroborated secondary sources; Apple's own pages don't state the exact timeout, so treat the "within an hour" detail as corroborated-but-not-primary-sourced). For a hobbyist audience this is a real support burden — expect "your app is broken/damaged" bug reports from users who haven't found the System Settings override.

## 3. Linux

There is **no OS-level gatekeeping equivalent to SmartScreen or Gatekeeper on Linux** — no package format requires a trusted signature to execute. Signing on Linux is a matter of ecosystem convention and integrity verification, not a runtime block.

- **AppImage**: Signing is optional and opt-in, not enforced. Per the official AppImage docs ([Signing AppImages](https://docs.appimage.org/packaging-guide/optional/signatures.html), docs.appimage.org): `appimagetool --sign` uses the system's `gpg`/`gpg2` to embed a signature, and "AppImages can be digitally signed by the person that has produced the AppImage. This ensures that the AppImage comes from the person who pretends to be the author, and ensures that the file has not been tampered with." Crucially, **the AppImage runtime itself does not validate the signature on launch** — a separate `validate` tool (from the AppImageUpdate project) is needed to check it, and nothing stops an unsigned AppImage from running. Tauri's own Linux signing docs ([Linux Code Signing](https://v2.tauri.app/distribute/sign/linux/), v2.tauri.app) confirm this directly: "While artifact signing is not required for your application to be deployed on Linux, it can be used to increase trust into your deployed application," and separately, "AppImage does not validate the signature, so you can't rely on it to check whether the file has been tampered with or not."
- **.deb / .rpm**: No signing requirement to build or run them standalone. Signing (with a GPG key trusted by APT/DNF) only matters if you operate your own APT/YUM repository that users add as a trusted source — irrelevant for a project just handing out downloadable installer files from GitHub Releases.
- **Flatpak / Flathub**: GPG signing exists at the OSTree repository layer (every commit to a Flatpak repo is signed), but if you submit to Flathub, **Flathub's own build and signing infrastructure handles this for you** — Flathub builds from your submitted manifest and source, and Flathub's own keys sign the resulting repo commits. Flathub's app requirements ([Requirements](https://docs.flathub.org/docs/for-app-authors/requirements), docs.flathub.org) focus on manifest structure, build-from-source, minimal permissions, and metadata completeness — they say nothing about the app author personally holding or managing a GPG key, because Flathub itself owns that step. Running your own independent Flatpak repo outside Flathub (not recommended for a solo hobbyist — extra hosting/ops burden) would require self-managing that GPG signing.

**Net for Linux: no signing cost is required at all**, and no user-facing warning dialog exists comparable to Windows/macOS. The one available option (GPG-sign the AppImage) is a trust nicety for advanced users, not something an ordinary user will hit friction over.

## 4. Tauri v2 updater plugin

Tauri's built-in updater plugin ([Updater | Tauri](https://v2.tauri.app/plugin/updater/), v2.tauri.app) uses its own cryptographic signing, completely separate from OS code-signing certificates:

- It uses a **minisign-based Ed25519 keypair**, generated locally via `tauri signer generate -w ~/.tauri/myapp.key` — nothing to do with Apple's Developer ID, Microsoft's Authenticode/Trusted Signing, or any CA.
- The public key goes into `tauri.conf.json` under `plugins.updater.pubkey`; the private key signs each release artifact at build time via `TAURI_SIGNING_PRIVATE_KEY` (and optional password) environment variables.
- **This signature is mandatory and cannot be disabled** — verbatim from the docs: "Tauri's updater needs a signature to verify that the update is from a trusted source. This cannot be disabled." If you ship the updater plugin at all, you must generate and manage this keypair, but it costs nothing and requires no identity verification with any third party.

**This minisign signature and OS code-signing are two entirely independent, non-substitutable systems.** The Tauri updater docs never mention Gatekeeper, notarization, or SmartScreen at all — confirmed by direct inspection of the page. Tauri's own platform-specific signing guides make the boundary explicit:

- The Windows signing guide ([Windows Code Signing](https://v2.tauri.app/distribute/sign/windows/), v2.tauri.app) states that without a separate OS-level Authenticode signature, the browser-downloaded installer triggers "SmartScreen warning that your application is not trusted and can not be started, when downloaded from the browser" — but also notes this "is not required to execute your application on Windows, as long as your end user is okay with ignoring the SmartScreen warning."
- The macOS signing guide ([macOS Code Signing](https://v2.tauri.app/distribute/sign/macos/), v2.tauri.app) states an unsigned/unnotarized app shows as "broken and can not be started" when downloaded from a browser, and that even ad-hoc signing "does not prevent macOS from requiring users to whitelist the installation in their Privacy & Security settings."

So: **the Tauri updater's minisign signature satisfies only Tauri's own update-integrity check. It does nothing for OS gatekeeping.** An update package can be perfectly validly minisign-signed and still get blocked/warned-on by SmartScreen or Gatekeeper on install, because those are unrelated trust systems checking unrelated signatures (Authenticode certificate chain vs. Apple Developer ID chain vs. an app-private Ed25519 key).

**Does the updater work at all for a non-OS-signed app, per platform?**

- **Linux**: Yes, cleanly. No OS gatekeeping exists to interfere, and Tauri's own Linux signing docs confirm OS-level signing "is not required for your application to be deployed on Linux." The minisign-signed AppImage/deb/rpm updates fine.
- **Windows**: Functionally yes — the updater's own minisign check will pass and the new binary will run — but every unsigned update reintroduces the SmartScreen "protected your PC" experience (or worse, since it may look like an in-place install rather than a fresh browser download, but the underlying binary is still unrecognized/zero-reputation on each new unsigned version, since reputation can't transfer between unsigned builds per Microsoft's own reputation docs).
- **macOS**: This is the sharpest edge. An installed macOS app auto-updating itself in-place is a different trust context than a fresh browser download, but an un-notarized update artifact still fails Gatekeeper's execution checks — Tauri's own docs describe the unsigned/unnotarized case as the app being reported "broken and can not be started." In practice, a non-notarized Tauri app's self-update flow on macOS is very likely to hit the same Gatekeeper wall as a fresh install, forcing the user back into the System Settings → Privacy & Security → Open Anyway dance for every single update — which largely defeats the point of having a silent auto-updater. This specific interaction (does Gatekeeper re-check on updater-driven relaunch, and does stapling matter here) is not something Tauri's or Apple's docs spell out explicitly for the updater-relaunch case specifically; treat this paragraph's practical conclusion as inference from documented Gatekeeper behavior plus Tauri's own "broken and can't be started" wording, not a directly-quoted primary-source statement about the updater flow itself.

## Decision table

| Option | Yearly cost | Covered | Not covered | Windows — user sees | macOS — user sees | Linux — user sees |
| --- | --- | --- | --- | --- | --- | --- |
| **A. Sign nothing, ship checksums + Tauri updater keypair** | $0 | Update-integrity via minisign (free, always required by Tauri anyway); SHA-256 checksums published alongside releases for manual verification | No OS trust on any platform | "Windows protected your PC" SmartScreen block-until-click-through on every release (reputation never builds — resets to zero on unsigned files); Smart App Control may hard-block on some Windows 11 machines | "App is damaged and can't be opened" / "not verified" dialog; user must go to System Settings → Privacy & Security → Open Anyway → Open, authenticate, for every fresh install and likely every auto-update too | No warning at all — AppImage/deb/rpm just run; may need `chmod +x` for AppImage |
| **B. macOS-only notarization** | $99/year (Apple Developer Program only) | Full Gatekeeper trust on macOS: signed + notarized + stapled, no warnings after first launch, auto-updates work cleanly | Windows still fully unsigned; Linux unaffected (already fine) | Same as Option A — SmartScreen block-until-click-through, no reputation buildup | Clean: standard "app downloaded from internet, verified developer" flow, or nothing at all if notarized+stapled; no System Settings detour needed | No warning (unaffected) |
| **C. Windows OV cert + macOS notarization** | ~$99–300+/year ($99 Apple + $150–300 OV cert from DigiCert/Sectigo/etc., since Azure Trusted Signing individual eligibility is US/Canada-only and this maintainer is not in that region) | Both major platforms get real OS trust; reputation builds over releases on Windows since the publisher identity is consistent across versions | Still costs real money annually on a "zero budget appetite" project; Linux unaffected (already fine) | SmartScreen still warns on first download of each *new* publisher/cert (expected — "several weeks and hundreds of clean installs" per Microsoft) but reputation now accumulates release-over-release instead of resetting; eventually few/no warnings | Clean, same as Option B | No warning (unaffected) |
| **D. Full signing everywhere (adds Flathub submission)** | Same $99–300+/year as C, plus ongoing maintenance overhead of a Flathub manifest/review process (no cash cost — Flathub build+signing is free) | Everything in C, plus a "verified" Flathub listing carrying Flathub's own build/signing trust for Linux users who prefer that distribution channel over a raw AppImage | Same as C | Same as C | Same as C | Flathub users get Flathub's own trust chain (no change for direct AppImage/deb downloads, which remain as in A/B/C) |

### Recommendation given "zero budget appetite"

Given the stated eligibility fact that Azure Trusted Signing is not available to this maintainer as an individual outside the US/Canada, the realistic **free-tier ceiling is Option A**, and the cheapest paid step up that meaningfully changes the user experience on the platform with the worst unsigned-app UX is **Option B (macOS notarization only, $99/year)** — because macOS's Gatekeeper friction (the "damaged, can't be opened" dialog plus a buried System Settings toggle) is more confusing and more likely to make a user abandon the app than Windows's comparatively well-known "More info → Run anyway" SmartScreen click-through. Before paying for anything, it's worth directly checking eligibility for **[SignPath Foundation](https://signpath.io)'s free OV code signing for open-source projects** as a possible $0 path to a trusted Windows certificate — this claim comes from Microsoft's own documentation pointing to it, but SignPath's specific acceptance criteria were not independently verified in this research pass.
