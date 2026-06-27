---
layout: post
date: 2026-06-25
title: EU DMA complaint against Alphabet over Play Integrity
author: Alexandro Sanchez Bach
---

For lack of a better place, I have posted my EU Digital Markets Act complaint against Alphabet over Play Integrity and Play Protect's unfair gatekeeping of alternative Android distributions here in my blog.

This text has minor editing, mainly to remove personal information and add additional links/resources. The core facts, concerns and requested actions remain unchanged.

The complaint below was submitted as an [Article 27](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R1925#art_27) third-party information report.

---

### Gatekeeper and services concerned

- Alphabet
    - [DMA.100002](https://digital-markets-act-cases.ec.europa.eu/cases/DMA.100002) - Google Play ("**Play**")
    - [DMA.100009](https://digital-markets-act-cases.ec.europa.eu/cases/DMA.100009) - Android Mobile ("**Android**")

### Technical and market context

Android provides a hardware-backed device integrity attestation mechanism (informally, "**Hardware Attestation API**" or "**Android Platform Key Attestation**") which enables third parties such as app developers to obtain digitally signed evidence of selected security-relevant properties and state of a connecting device [[1]](https://web.archive.org/web/20260617093031/https://developer.android.com/privacy-and-security/security-key-attestation), including verified-boot keys associated with the loaded Android operating system image, and enforce access controls accordingly.

*Google Play Integrity API* (or "**Play Integrity**") is a *Google Play* service that allows app developers to "*check that user actions and server requests are coming from [their] genuine app, installed by Google Play, <mark>running on a genuine and certified Android device</mark>*" [[2]](https://web.archive.org/web/20260617092956/https://developer.android.com/google/play/integrity/overview). Play Integrity builds on Android Platform Key Attestation signals and moves the responsibility of managing approved verified-boot keys away from app developers; in Google's words: "_Play Integrity API is the recommended way to benefit from hardware-backed Android platform key attestation_" [[3]](https://web.archive.org/web/20260616005723/https://android-developers.googleblog.com/2025/10/stronger-threat-detection-simpler.html).

Google presents Play Integrity to app developers as part of Google Play's *Protected with Play* (or "**Play Protect**")  security services, alongside messaging such as "*Protect your app and your users*", "*Detect security threats and risky devices*" and "*core features critical to building secure apps*" [[4]](./play_protect_developers_ex1.png) [[5]](https://web.archive.org/web/20260621025340/https://play.google.com/console/about/app-integrity/) [[6]](https://web.archive.org/web/20260619024311/https://developer.android.com/privacy-and-security/security-tips#app_integrity).

Play Integrity's device-integrity verdicts since Android 13 require, among other criteria, hardware-backed proof that the loaded Android operating system is a "*certified device manufacturer image*" [[7]](https://web.archive.org/web/20260623173041/https://developer.android.com/google/play/integrity/verdicts). Google refers to this broader device status as "**Play Protect certified**" [[8]](https://web.archive.org/web/20260607171012/https://support.google.com/googleplay/answer/7165974), which is available for device manufacturers, but not to third-party Android distributions made for existing supported devices [[9]](https://web.archive.org/web/20260622132415/https://www.android.com/certified/).

Obtaining *Play Protect certified* status requires device manufacturers to pass "**Android compatibility**" device validation [[10]](https://web.archive.org/web/20260627100624/https://source.android.com/docs/compatibility/compatibility-faq) and to become Google Mobile Services (GMS) partners [[11]](https://web.archive.org/web/20260625223004/https://www.android.com/gms/) [[12]](https://web.archive.org/web/20260530050020/https://www.android.com/gms/contact/). Such Android compatibility requires compliance with Android's _Compatibility Definition Document_ (CDD) and passing the _Compatibility Test Suite_ (CTS), which include both hardware and software requirements [[13]](https://web.archive.org/web/20260627100644/https://source.android.com/docs/compatibility/overview), covering both security and non-security criteria [[14]](https://web.archive.org/web/20260627100723/https://source.android.com/docs/compatibility/17/android-17-cdd#9_security_model_compatibility).

### DMA concerns

Alphabet operates Play Integrity in a way that gatekeeps which Android Mobile environments may access Google Play applications, while providing no fair, reasonable and non-discriminatory approval path for secure third-party Android Mobile environments. This may undermine Alphabet’s DMA obligations as gatekeeper for both Google Play and Android Mobile.

In particular:

- Google's Play Protect certification path does not appear to provide a fair, reasonable, non-discriminatory process for third-party Android Mobile distributors to have their verified-boot keys recognised for existing Android devices that support alternative operating systems.
- As a result, secure non-Google-certified Android operating systems such as GrapheneOS can be excluded from apps and services using Play Integrity even where their supported devices meet all security requirements laid out in Android's Compatibility Test Suite.
- This risks misleading app developers by treating "not Google-certified" as equivalent to "not secure", while encouraging developers to use Play Integrity as a security best practice and access-control mechanism.
- The practical effect is that Google Play can break Android Mobile hardware-software interoperability: alternative Android operating systems cannot interoperate on equal terms with the same Android hardware-backed security features if Play Integrity refuses to recognise their verified-boot keys under objective criteria.

This raises the following DMA concerns:

- [*Article 6(7)*](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R1925#art_6): Play Integrity appears to restrict effective interoperability between Android Mobile features. Any integrity restriction should be strictly necessary, proportionate and duly justified. Refusal to recognise alternative verified-boot keys is not the least restrictive way to protect device integrity where existing Android platform key attestation can provide comparable security evidence.
- [*Article 13*](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R1925#art_13): A technical security service such as Play Integrity should not be designed or operated in a way that undermines effective compliance with DMA obligations by making device-manufacturer status or GMS partnership the only practical route to app access under Play Integrity.

### Requested action and possible remedy

I ask the Commission to assess whether Alphabet’s design and operation of Google Play's _Play Integrity API_, including the absence of an objective Play Protect certification process for alternative Android Mobile distributions for existing devices, undermines or circumvents Alphabet's DMA obligations in relation to Google Play and Android Mobile.

A proportionate remedy would require Alphabet to provide a transparent, objective, non-discriminatory process by which alternative Android operating systems could be _Play Protect certified_ (or equivalent recognition for Play Integrity verdict purposes) when they, in conjunction with an existing supported device, show compliance with _Android compatibility_ requirements.
