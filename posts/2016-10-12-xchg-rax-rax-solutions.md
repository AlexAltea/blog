---
layout: post
date: 2016-10-12 00:00:00 UTC
title: Solutions of xchg rax,rax
---

## Introduction

In words of *xorpd*, the author of `xchg rax,rax`:

> `xchg rax,rax` is a collection of assembly gems and riddles I found over many years of reversing and writing assembly code. The book contains 0x40 short assembly snippets, each built to teach you one concept about assembly, math or life in general.

The original release, which can be read online at [1], contains no official solutions, and some of the snippets doesn't even seem to yield a clearly defined "answer". Also, in his own words:

> > Is that the content of your book? Some assembly language instructions without comments?
>
> Yes.
>
> > Is that a bad joke?
>
> No, arranging almost meaningless sequences of assembler instructions against a black background is a form of **art**. You may call it *nerd poetry*.

Nevertheless, I recovered from old backups my own thoughts and solutions for some of the snippets, and uploaded them just in case it could be useful or interesting for someone.

[1] [http://www.xorpd.net/pages/xchg_rax/snip_00.html](http://www.xorpd.net/pages/xchg_rax/snip_00.html)

## Solutions

### Snippet 0x00

Different ways of setting several general purpose registers to *0*.


### Snippet 0x01

Computes the `rcx`-th term of the Fibonacci sequence, assuming the initial state `rax=0`, `rdx=1`.


### Snippet 0x02

Boolean cast: `rax := bool(rax)`, i.e. `rax := rax ? 1 : 0`.


### Snippet 0x03

Minimum function: `rax := min(rax, rdx)`.


### Snippet 0x04

Replaces uppercase with lowercase characters and viceversa.


### Snippet 0x05

Allows to branch depending on whether `rax` is in range *[5,9]* using only one `jbe` jump.


### Snippet 0x06

Does nothing since the instructions cancel each other.


### Snippet 0x07

Does nothing since the instructions cancel each other.


### Snippet 0x08

Computes the average, i.e. `rax := (rax + rdx) / 2`.

Note that it prevents overflow issues since `rcr` does a 33-bit rotation using the `CF` flag.


### Snippet 0x09

Computes `rax := (rax + 4) / 8`.

Note this is computing `rax / 8` and rounding to the nearest integer (thanks [@ZaneH](https://github.com/ZaneH)).


### Snippet 0x0A

Increments by one an **arbitrarily long** little-endian integer at `rdi`.


### Snippet 0x0B

Toggles between not (`~`) and negation (`-`) based on the value of `rax`.
```
if (rax)
  rdx = ~rdx
else
  rdx = -rdx
```

Note that `rax` is also negated as a side-effect.

*TODO: Not sure if there's anything else special about this.*


### Snippet 0x0C

Registers `rax`, `rcx` end up with the same value, thanks to distributivity of ROR (with XOR).
```
rcx = rax
rcx = (rcx ^ rbx) >> 13
rax = (rax >> 13) ^ (rbx >> 13)
```


### Snippet 0x0D

Registers `rdx`, `rbx` end up with the same value, thanks to distributivity of AND (with XOR) and commutativity of XOR.
```
rdx = rbx
rbx = (rbx & rax) ^ (rcx & rax)  // Associativity of AND
rax = (rdx & rax) ^ (rcx & rax)  // Commutativity of XOR
```


### Snippet 0x0E

Registers `rax`, `rcx` end up with the same value, thanks to DeMorgan's law.
```
rcx = rax
rcx = ~(rcx & rbx)
rax = ~rax | ~rbx
```


### Snippet 0x0F

Computes the following:
```
rsi[0] ^= al
rsi[1] ^= rsi[0]
rsi[2] ^= rsi[1]
rsi[3] ^= rsi[2]
...
```

*TODO: Not sure if there's anything else special about this.*


### Snippet 0x10

Different ways of swapping the contents of `rax` and `rcx`.


### Snippet 0x11

Compares two strings `rsi` and `rdi`. If the register `rax` is zero-initialized, it will remain as *0* unless the strings differ.

*TODO: Not sure if there's anything else special about this.*


### Snippet 0x12

Computes `(rax | rdx) + (rax & rdx)`, which can be simplified to `rax + rdx`.


### Snippet 0x13

Computes `rax + rbx`.

See also: https://en.wikipedia.org/wiki/Adder_(electronics)


### Snippet 0x14

Computes the average rounded to the lowest integer, i.e. `rax := floor((rax + rdx) / 2)`.


### Snippet 0x15

Casts the `int32_t` value in `eax` to an `int64_t` value in `rax`.

Note that this requires the 32 most significant bits in `rax` to be cleared.


### Snippet 0x16

*TODO: No idea about this one.*


### Snippet 0x17

Computes the absolute value of `rax`, i.e. `rax := abs(rax)`.


### Snippet 0x18

Compares two timestamps.

The instruction `rdtsc` stores the current 64-bit timestamp counter value in `edx:eax`, while the `shl` and `or` instructions aggregate the halves of each register into `rax`.

*TODO: Not sure if there's anything else special about this.*


### Snippet 0x19

Calls `print_str("hello world!");`.

The return value of `.skip` is the address to the hardcoded string, and due to the stack layout, this will implicitly become the first argument of `print_str`.


### Snippet 0x1A

Gets the `rip` register after the call instruction, i.e. `rax := .next`.


### Snippet 0x1B

Indirect branch to `rax`. Since there's no immediate arguments to cause further stack cleanup, this is equivalent to `jmp rax`.
                                                             

### Snippet 0x1C

Swaps the stack pointer with the address at the top of the current stack.

*TODO: Not sure if there's anything else special about this.*


### Snippet 0x1D

Copies `buff1` to `buff2`. The extra `+1` and `+8` take care of the side effects of `enter`, such as the extra values added before and after the buffer.

Note that the `buff2` should be 16 bytes larger than `buff1`, specifically with 8 bytes of padding at the beginning and at the end to prevent OOB writes after executing the `enter` instruction.
