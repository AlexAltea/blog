---
layout: post
date: 2018-04-18 00:00:00 UTC
title: LLE vs HLE and their tradeoffs
author: Alexandro Sanchez
---

## Introduction

This article aims to give an intuitive understanding for the terms "*Low-Level Emulation*" (LLE) and "*High-Level Emulation*" (HLE) often heard in the emulation scene, their differences and tradeoffs in development/performance costs, and how developers choose one paradigm or the other.

Machines are made of several *layers of abstraction*, each of them relying in the layer below to perform some particular task. In the context of gaming consoles, you might consider these layers (ordered from higher to lower level):

- Game
- Game engine
- System libraries
- Kernel/drivers
- Hardware
 
That's where these "*low-level*" or "*high-level*" terms come from. Something is more "*high-level*" when it has more layers of abstraction below it, and it's more "*low-level*" when it has more layers of abstraction above it. With so many layers, the terms "low" and "high" can become quite subjective (developers can't even agree about whether some emulators are HLE or LLE). Furthermore, you could go even below than hardware-level and start thinking about transistors, atoms, etc. as even deeper layers of abstraction. Similarly, there's also even higher levels like the game scripts that are sometimes used to handle events/dialogues in a game. Of course, for most emulators, these layers are either too low, or too high. Why?

## Emulation paradigms

Let's tackle this question after giving an intuitive notion of what emulation is. Emulating a system all about putting a "*barrier*" between two adjacent layers of abstraction. For instance:
 
- "*LLE emulators*" ([EPSXE](http://www.epsxe.com/), [PCSX2](https://pcsx2.net/)): They put the barrier between the hardware and the kernel. The entire software stack would run as usual thinking it's on a real PS1, PS2 etc., but whenever the hardware is accessed (e.g. PCI configuration registers, MMIO accesses, etc.) the emulator would intercept that and execute whatever the emudevs wanted. This is the reason why you get the original console menus and the overall "look and feel" of the console.
- "*HLE emulators*" ([RPCS3](https://rpcs3.net/), [Citra](https://citra-emu.org/)): They put the barrier between the kernel and userland (i.e. applications, games, etc.). The application runs as usual (of course, after translating userland instructions), but whenever it needs to access the operating system (e.g. to open files, to map memory, to create threads), that request aka. syscall will be intercepted and handled by some code written by the emudevs. This is the reason why you can typically just drag-and-drop a game and start playing it without booting any underlying OS.
 
Back to the original question, why do emulators pick the barriers always at these two "hot spots", i.e. LLE (hardware and kernel) and HLE (kernel and userland)?
 
When you place this "emulation" barrier between two layers, you have to **reimplement** the layer below (i.e. reimplement the hardware on LLE, reimplement the kernel on HLE), so that the layer(s) above it can **execute** successfully. This results in two costs that you have to balance: "*development time*" and "*execution time*". Let me explain why this balance is important with few extreme examples of poor balances:
 
- *Too high-level*: What would happen if you'd put that barrier between the game engine and the actual game? This idea used to be not so crazy, as it's what https://www.scummvm.org/ does. However, game engines these days are insanely complex with several million lines of code, it would take you centuries as a single developer to write an emulator that operated at such high levels. The "*development time*" would be massive, but the "*execution time*" (i.e. the emulator's performance) would be pretty good, since all the complex tasks have been reimplemented natively for the host system.
 
- *Too low-level*: What would happen if you wrote a transistor-level emulator? Again, not so crazy for old platforms, see the http://www.visual6502.org/ project. Assuming you had the equipment to decap a chip, a scanning electron microscope and fancy computer vision algorithms, you could easily generate code that simulates your target microprocessor, so little "*development time*", however, the "*execution time*" would be insanely high caused by simulating billions of transistors.
 
As you see, the rule of thumb is: higher-level incurs in larger development costs, and lower-level incurs in larger execution costs. But this is not always the case, and it has frequently led to misconceptions among the end-users. One of them is wrongly estimating the perfomance of different emulator paradigms.

## Performance myths

Let's debunk some of those performance myths: Assume you want to emulate some machine, and you are learning about its hardware/software to balence "*development time*" vs "*execution time*" and pick the right strategy. How do you estimate those costs, specially "*execution time*", aside from the naive rule of thumb above? Estimating how fast something will run isn't just about which levels of abstraction you are targetting. The resulting performance will be depend on how many "*concepts*" from your *guest machine* (i.e. the thing you're trying to emulate), can be mapped into your *host machine* (the thing that will run the emulator).
 
To give you an example, one such "*concept*" is the MMU. To explain it briefly (and slightly wrong/oversimplified but for the sake of the explanation will do), the MMU is the thing that allows each application have access to a slice of RAM by mapping addresses of a "*virtual address space*" (an imaginary arrangement of memory) to a "*physical address space*" (the actual RAM). Every time the application accesses the memory with some CPU instruction, behind the scenes the MMU will translate the virtual address given by the application into a physical one.
 
- HLE emulators typically don't worry about the guest MMU since guest applications only use virtual addressing and whenever they try to contact the guest kernel (e.g. to allocate more memory), the emulator takes control and very generously gives the guest application a chunk of its own host virtual memory. So everyone's happy.
 
- LLE emulators have to worry about both the guest virtual memory and the guest physical memory. Many of them allocate guest physical memory during initialization, and do the "*guest virtual memory* to *guest physical memory*" translation by emulating the MMU on software. That causes every memory access (1 instruction) to invoke some specialized code that does the translation+access (100's of instructions). Of course, some translations can be cached, but the performance hit is still high. Remember that for every guest access, you have to traverse 4 layers:

    1. Guest virtual memory
    2. Guest physical memory
    3. Host virtual memory
    4. Host physical memory
 
However in some scenarios (this depends on MMU quirks, page sizes, etc.), you could have use your host computer's own MMU to handle the accesses of the guest applications directly. One way of accomplishing this is running the guest software in a VM and having an hypervisor letting it directly access a slice of the host computer's physical RAM directly. This would remove the need for expensive software-based address translation and result in large performance gains.

## Conclusion

By making a better use of the host machine's resources, in the MMU and many other different areas, you can make even low-level emulation happen with an acceptable performance. It's not a surprise that Sony used this strategy to emulate the PS2 on the PS3, and Microsoft to emulate the Xbox on Xbox 360 [[1]](http://michaelbrundage.com/project/xbox-360-emulator/) and Xbox 360 on Xbox One. This 10x performance slowdown while doing LLE is a myth, resulting from many oversimplifications and/or people that have poorly utilized the host machine's resources.
 
Of course, massive slowdowns can still happen: with really heterogeneous architectures, some concepts can be hard to map into each other and you might have to resort to software emulation incurring in 10x and 100x performance penalties, but this isn't always necessarily the case. There are no magic "*performance penalty*" numbers, everything has to be considered in a case-by-case basis, and the only way of estimating what that would be is getting to know both guest and host systems really in detail.
