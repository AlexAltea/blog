---
layout: post
date: 2019-02-16
title: PS3/Cell Cryptomining: Wide arithmetic on SPUs
author: Alexandro Sanchez
---

[TOC]

## Background

Some time ago, I implemented a cryptocurrency miner for the [Cell B.E. Architecture](https://en.wikipedia.org/wiki/Cell_(microprocessor)) used in the PlayStation 3 and certain servers. Specifically, the goal was implementing PoW-algorithms based on CryptoNight, described by the [CryptoNote](https://cryptonote.org/standards/) standards and used by [Monero/XMR](https://www.getmonero.org/).

At their current valuation, no such cryptocurrency can be profitably mined using consumer PlayStation 3 hardware and this situation is not expected to revert in the short/mid term. Furthermore, possible long-term changes are irrelevant, as newer hardware will increasingly outperform the Cell B.E., raising mining difficulty and the profitability threshold ever further.

Consequently, I'm releasing the source code of this miner along with blog articles on technical aspects of Cell B.E. that might be of general interest (even if just for historical reasons):

1. [PS3/Cell Cryptomining: Wide arithmetic on SPUs](.).
2. [PS3/Cell Cryptomining: High-performance AES on SPUs](#). (TBD.)
3. [PS3/Cell Cryptomining: Memory Flow Controller](#). (TBD.)

This first post describes the implementation of wide arithmetic operations on "narrow" ALUs present in the SPUs.

## Multiplication (64-bit)

CryptoNight requires a 64-bit x 64-bit integer multiplication that results in a 128-bit integer. Implementing such operation on the SPUs is challenging as the largest multiplication granularity available is 16-bit x 16-bit to 32-bit due to the word-size limitations of the SPU ALUs. The following algorithm describes how to emulate such multiplication.

### Theory

Consider the `a` and `b` input registers, the 64-bit LHS and RHS of the multiplication operation are composed of the half-words [a0, a1, a2, a3] and [b0, b1, b2, b3], respectively.

```
   0        16       32       48       64       80       96       112      128
   +--------+--------+--------+--------+--------+--------+--------+--------+
a: |   a0   |   a1   |   a2   |   a3   |   XX   |   XX   |   XX   |   XX   |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
b: |   b0   |   b1   |   b2   |   b3   |   XX   |   XX   |   XX   |   XX   |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   MSB                                                                     LSB
```

This is equivalent to the following representation:

```
LHS := a3 + (a2 * 2^16) + (a1 * 2^32) + (a0 * 2^48)
RHS := b3 + (b2 * 2^16) + (b1 * 2^32) + (b0 * 2^48)
```

Applying the distributive property, the multiplication of both values should be equivalent to:

```
LHS * RHS = (a3 + (a2 * 2^16) + (a1 * 2^32) + (a0 * 2^48)) *
            (b3 + (b2 * 2^16) + (b1 * 2^32) + (b0 * 2^48))
          = (a3*b3*2^00) + (a3*b2*2^16) + (a3*b1*2^32) + (a3*b0*2^48) +
            (a2*b3*2^16) + (a2*b2*2^32) + (a2*b1*2^48) + (a2*b0*2^64) +
            (a1*b3*2^32) + (a1*b2*2^48) + (a1*b1*2^64) + (a1*b0*2^80) +
            (a0*b3*2^48) + (a0*b2*2^64) + (a0*b1*2^80) + (a0*b0*2^96)    
```

Our implementation will perform these 16 multiplications of 16-bit words (`aX*bY`), shift the results (`*2^N`), and add everything together using 128-bit additions.

### Implementation

First of all, let's recap the available multiplication operations in SPU (quoted from the *Synergistic Processor Unit Instruction Set Architecture v1.2*):

> * `mpy rt,ra,rb`: **Multiply**. The signed 16 least significant bits of the corresponding word elements of registers `ra` and `rb` are multiplied, and the 32-bit products are placed in the corresponding word elements of register `rt`.
> * `mpyhh rt,ra,rb`: **Multiply high high**. The signed 16 most significant bits of the word elements of registers `ra` and `rb` are multiplied, and the 32-bit products are placed in the corresponding word elements of register `rt`.

When necessary, unsigned variants are available by adding an `u` suffix to the instruction name.

#### 1. Multiplying half-words

The distributive unfolding of the multiplication described earlier involves multiplying 16 half-words pairs into 16 words. Each multiplication instruction yields a maximum of 4 32-bit words, but since only 64-bits are used in `a` and `b`, only 2 are useful.

To minimize the number of multiplications, we can duplicate/shuffle half-words to the unused 64-bits of the quad-word via `shufb` as follows (this step can also be used to switch endianness, if necessary):

```
   0        16       32       48       64       80       96       112      128
   +--------+--------+--------+--------+--------+--------+--------+--------+
a: |   a0   |   a1   |   a2   |   a3   |   a2   |   a3   |   a0   |   a1   |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
b: |   b0   |   b1   |   b2   |   b3   |   b0   |   b1   |   b2   |   b3   |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   MSB                                                                     LSB
```

Additionally, we left-shift by 16 both `a`, `b` into `c`, `d` respectively, to do high-low multiplications (similarly to the `mpyh` instruction but without post-shifting). It does not matter whether the least significant half-word is zeroed. The result is:

```
   0        16       32       48       64       80       96       112      128
   +--------+--------+--------+--------+--------+--------+--------+--------+
c: |   a1   |  (a2)  |   a3   |  (a2)  |   a3   |  (a0)  |   a1   |  (00)  |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
d: |   b1   |  (b2)  |   b3   |  (b0)  |   b1   |  (b2)  |   b3   |  (00)  |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   MSB                                                                     LSB
```

This way we can generate all necessary multiplications as follows:

```
mpy     t0, a, b
mpyhh   t1, a, d
mpyhh   t2, b, c
mpyhh   t3, a, b
```

Leaving us with the following results:

```
   0        16       32       48       64       80       96       112      128
   +--------+--------+--------+--------+--------+--------+--------+--------+
t0 |     a1 * b1     |     a3 * b3     |     a3 * b1     |     a1 * b3     |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
t1 |     a0 * b1     |     a2 * b3     |     a2 * b1     |     a0 * b3     |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
t2 |     b0 * a1     |     b2 * a3     |     b0 * a3     |     b2 * a1     |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
t3 |     a0 * b0     |     a2 * b2     |     a2 * b0     |     a0 * b2     |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   MSB                                                                     LSB
```

#### 2. Shuffling half-words

Before adding each of these 16 words, we need to multiply each by the corresponding power of 2 computed previously (i.e. shifting by a certain amount in bits). These constants are:

```
   0        16       32       48       64       80       96       112      128
   +--------+--------+--------+--------+--------+--------+--------+--------+
t0 | t00          64 | t01           0 | t02          32 | t03          32 |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
t1 | t10          80 | t11          16 | t12          48 | t13          48 |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
t2 | t20          80 | t21          16 | t22          48 | t23          48 |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
t3 | t30          96 | t31          32 | t32          64 | t33          64 |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   MSB                                                                     LSB
```

We need to move these words into their proper locations (note that some words like `t02` or `t30` are already well placed). Using scratch registers is necessary, since working directly on {t0, t1, t2, t3} would cause bits to get lost due to overlaps. Doing this naively would involve using 16 scratch registers, i.e. 16 128-bit integers to be added later on.

However, by shuffling bytes via `shufb` we can bring this down to only 7 scratch registers:

```
   128      112      96       80       64       48       32       16       0
   +--------+--------+--------+--------+--------+--------+--------+--------+
v0 |                 | ##### t00 ##### | ##### t02 ##### | ##### t01 ##### |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
v1 | ##### t30 ##### | ##### t32 ##### | ##### t31 ##### |                 |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
v2 |                 | ##### t33 ##### | ##### t03 ##### |                 |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
v3 |        | ##### t10 ##### | ##### t12 ##### | ##### t11 ##### |        |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
v4 |        | ##### t20 ##### | ##### t22 ##### | ##### t21 ##### |        |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
v5 |                          | ##### t13 ##### |                          |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   +--------+--------+--------+--------+--------+--------+--------+--------+
v6 |                          | ##### t23 ##### |                          |
   +--------+--------+--------+--------+--------+--------+--------+--------+
   MSB                                                                     LSB
```

This is accomplished by the following operations (note that only 5 shuffle masks are necessary):

```
shufb   v0, t0, t0, mask_v0
shufb   v1, t3, t3, mask_v1
shufb   v2, t0, t3, mask_v2
shufb   v3, t1, t1, mask_v3_v4
shufb   v4, t2, t2, mask_v3_v4
shufb   v5, t1, t1, mask_v5_v6
shufb   v6, t2, t2, mask_v5_v6
```

#### 3. Adding results

The final step is adding the 7 resulting 28-bit words {v0, ..., v6} as described by the algorithm "*Addition (128-bit)*". Let such algorithm be implemented by the macro `add_128(output, lhs, rhs)`. The final result `r` of the multiplication algorithm is computed as follows:

```
add_128  t0, v0, v1
add_128  t1, v2, v3
add_128  t2, v4, v5
add_128  t0, t0, t1
add_128  t0, t0, t2
add_128   r, t0, v6
```

As a final step, one might shuffle bytes again to match the desired endianness.

## Addition (128-bit)

During the implementation of "*Multiplication (64-bit)*" we required a 128-bit + 128-bit integer addition that results in a 128-bit integer, but the largest granularity we can achieve for additions in SPUs is 32-bit. Although our approach here is relatively straightforward, we document it here for the sake of completeness.

### Theory

Consider the `a` and `b` input registers and the `s` output register, the 128-bit LHS and RHS of the addition operation composed of the 32-bit words [a0, a1, a2, a3] and [b0, b1, b2, b3], respectively.

```
   0                 32                64                96                128
   +-----------------+-----------------+-----------------+-----------------+
a: |        a0       |        a1       |        a2       |        a3       |  
   +-----------------+-----------------+-----------------+-----------------+
   +-----------------+-----------------+-----------------+-----------------+
b: |        b0       |        b1       |        b2       |        b3       |
   +-----------------+-----------------+-----------------+-----------------+
   MSB                                                                     LSB
```

This is equivalent to the following representation:

```
LHS := a3 + (a2 * 2^32) + (a1 * 2^64) + (a0 * 2^96)
RHS := b3 + (b2 * 2^32) + (b1 * 2^64) + (b0 * 2^96)
```

Similar to four-bit adder, we perform the addition component-wise propagating the carry bit from the LSW to the MSW. We represent this carry-bit with the `overflow` (shortened as `o`), that takes an addition result and outputs 1 if the addition is >= 2^32, and 0 otherwise.

```
s3 = a3 + b3
s2 = a2 + b2 + overflow(s3)
s1 = a1 + b1 + overflow(s2)
s0 = a0 + b0 + overflow(s1)
```

### Implementation

First of all, let's recap the available multiplication operations in SPU (quoted from the *Synergistic Processor Unit Instruction Set Architecture v1.2*):

> * `a rt,ra,rb`: **Add Word**. Each word element of register `ra` is added to the corresponding word element of register `rb`, and the results are placed in the corresponding word elements of register `rt`.
> * `cg rt,ra,rb`: **Carry Generate**. Each word element of register `ra` is added to the corresponding word element of register `rb`. The carry out is placed in the least significant bit of the corresponding word element of register `rt`, and 0 is placed in the remaining bits of `rt`.
> * `shlqbyi rt,ra,value`: **Shift Left Quadword by Bytes Immediate**. The contents of register `ra` are shifted left by the number of bytes specified by the unsigned 5-bit `value`. The result is placed in register `rt`.

#### 1. Basic idea

By using these instructions, we can perform this addition as follows:

```
   +-----------------+-----------------+-----------------+-----------------+
t0 | t00:   a0 + b0  | t01:   a1 + b1  | t02:   a2 + b2  | t03:   a3 + b3  |
   +-----------------+-----------------+-----------------+-----------------+
c0 | c00: o(a1 + b1) | c01: o(a2 + b2) | c02: o(a3 + b3) |                 |
   +-----------------+-----------------+-----------------+-----------------+
   +-----------------+-----------------+-----------------+-----------------+
t1 | t10:   t00+c00  | t11:   t01+c01  | t12:   t02+c02  |                 |
   +-----------------+-----------------+-----------------+-----------------+
c1 | c10: o(t01+c01) | c11: o(t02+c02) |                 |                 |
   +-----------------+-----------------+-----------------+-----------------+
   +-----------------+-----------------+-----------------+-----------------+
t2 | t20:   t10+c10  | t21:   t11+c11  |                 |                 |
   +-----------------+-----------------+-----------------+-----------------+
c2 | c20: o(t11+c11) |                 |                 |                 |
   +-----------------+-----------------+-----------------+-----------------+
   +-----------------+-----------------+-----------------+-----------------+
t3 | t30:   t20+c20  |                 |                 |                 |
   +-----------------+-----------------+-----------------+-----------------+
```

Here, at each iteration *N = {0,1,2,3}*, the temporary variable *tN* contains the 32-bit componentwise addition of *tN-1* and *cN-1*. This can easily be done with the `a` instruction described before. The temporary variables *cN* contain the word-shifted carry bit of said addition, which can be achieved by a combination of the `cg` and `shlqbyi` instructions.

This process is kickstarted by computing the addition and shifted overflow of the original LHS and RHS components into the *t0* and *c0* registers respectively. The final output register `r` can simply be computed as [t30, t21, t12, t03].

#### 2. Optimizing register usage

By analyzing dependencies, you might observe that no more than 3 temporary variables are used at any time. Let's redefine these as `t0`, `t1`, `t2`. Additionally, given that left-shifts are always zero-extended, we can preserve the LSWs as we "carry on" with the computation (no pun intended), saving us from cherry-picking words from different temporaries into `r`.

The final algorithm would look like this:

```
cg         t1, lhs, rhs
a          t0, lhs, rhs
shlqbyi    t1, t1, 4
cg         t2, t0, t1
a          t0, t0, t1
shlqbyi    t2, t2, 4
cg         t1, t0, t2
a          t0, t0, t2
shlqbyi    t1, t1, 4
a           r, t0, t1
```

Note that the same approach is used to perform 64-bit additions, required in CryptoNight's Memory-Hard Loop.

## Sources

You can find the source code for these implementations in: [`arithmetic.s`](arithmetic.s).
