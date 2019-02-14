---
layout: post
date: 2016-09-07 00:00:00 UTC
title: Fast lookups in JIT-compiled maps
---

This post shows a way of optimizing lookup performance in maps associating integer keys to arbitrary data.

## Background

Some time ago, I reimplemented the [RSX GPU](https://en.wikipedia.org/wiki/RSX_%27Reality_Synthesizer%27) command processor in the emulator, [Nucleus](https://github.com/AlexAltea/nucleus). This GPU is made of several engines, each bound at a specific index (*0*-*7*) of the command processor, and each index provides a MMIO register window (*0x0*-*0x1FFC*). Commands are 16-bit bitfields containing an index (3-bit) and MMIO offset (13-bit). Recent userland drivers always bound engines to the same indices and there was a limited number valid MMIO offsets, our command processor was just a big hardcoded *switch-case* mapping commands to corresponding emulator function.

However, older or custom drivers might bind engines at different indices making our compile-time *switch-case* useless. Ignoring wasted memory, a static array of 2^16 entries could be a fast solution. Nevertheless, 32-bit or 64-bit commands could have made this impossible. Since lookup times are critical, this yields the question, **what's the fastest way of doing a lookup in a set of sparse commands -or sparse non-random integers- generated at runtime?** Should we use huge static arrays? Should we use hash tables? Which data structure will optimize lookup time?

Jitter solves this by letting the compiler decide that.

---

__TODO: More information soon.__
