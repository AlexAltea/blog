/**
 * SPU high-performance wide arithmetic.
 * Author: Alexandro Sanchez Bach <alexandro@phi.nz>.
 */

// Registers

#define alu_reg_se32       $80
#define alu_reg_se64       $81
#define alu_reg_se128      $82
#define alu_reg_mul_lhs    $83
#define alu_reg_mul_rhs    $84
#define alu_reg_mul_m0     $85
#define alu_reg_mul_m1     $86
#define alu_reg_mul_m2     $87
#define alu_reg_mul_m3     $88
#define alu_reg_mul_m4     $89
#define alu_reg_add_m64    $90

#define alu_reg_i0         $40
#define alu_reg_i1         $41
#define alu_reg_t0         $42
#define alu_reg_t1         $43
#define alu_reg_t2         $44
#define alu_reg_t3         $45
#define alu_reg_v0         $46
#define alu_reg_v1         $47
#define alu_reg_v2         $48
#define alu_reg_v3         $49
#define alu_reg_v4         $50
#define alu_reg_v5         $51
#define alu_reg_v6         $52

// Constants

    .align 4
    .global alu_endian
alu_endian:
    // swap-endian-32
    .byte  0x03, 0x02, 0x01, 0x00, 0x07, 0x06, 0x05, 0x04
    .byte  0x0B, 0x0A, 0x09, 0x08, 0x0F, 0x0E, 0x0D, 0x0C
    // swap-endian-64
    .byte  0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00
    .byte  0x0F, 0x0E, 0x0D, 0x0C, 0x0B, 0x0A, 0x09, 0x08
    // swap-endian-128
    .byte  0x0F, 0x0E, 0x0D, 0x0C, 0x0B, 0x0A, 0x09, 0x08
    .byte  0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00

    .align 4
    .global alu_wswap
alu_wswap:
    // mul_lhs: switch endian, then word swap [0,1,2,3] -> [0,1,1,0]
    .byte  0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00
    .byte  0x03, 0x02, 0x01, 0x00, 0x07, 0x06, 0x05, 0x04
    // mul_rhs: switch endian, then word swap [0,1,2,3] -> [0,1,0,1]
    .byte  0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00
    .byte  0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00

    .align 4
    .global alu_mul64_constants
alu_mul64_constants:
    // v0
    .byte  0x80, 0x80, 0x80, 0x80, 0x00, 0x01, 0x02, 0x03
    .byte  0x08, 0x09, 0x0A, 0x0B, 0x04, 0x05, 0x06, 0x07
    // v1
    .byte  0x00, 0x01, 0x02, 0x03, 0x08, 0x09, 0x0A, 0x0B
    .byte  0x04, 0x05, 0x06, 0x07, 0x80, 0x80, 0x80, 0x80
    // v2
    .byte  0x80, 0x80, 0x80, 0x80, 0x1C, 0x1D, 0x1E, 0x1F
    .byte  0x0C, 0x0D, 0x0E, 0x0F, 0x80, 0x80, 0x80, 0x80
    // v3+v4
    .byte  0x80, 0x80, 0x00, 0x01, 0x02, 0x03, 0x08, 0x09
    .byte  0x0A, 0x0B, 0x04, 0x05, 0x06, 0x07, 0x80, 0x80
    // v5+v6
    .byte  0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x0C, 0x0D
    .byte  0x0E, 0x0F, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80

    .align 4
    .global alu_add64_constants
alu_add64_constants:
    .byte  0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00
    .byte  0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00

// Macros

#define add_64(ret, lhs, rhs)                                                \
    shufb   alu_reg_t0, lhs, lhs, alu_reg_se64                              ;\
    shufb   alu_reg_t1, rhs, rhs, alu_reg_se64                              ;\
    cg      alu_reg_t2, alu_reg_t0, alu_reg_t1                              ;\
    a       alu_reg_t0, alu_reg_t0, alu_reg_t1                              ;\
    shlqbyi alu_reg_t2, alu_reg_t2, 4                                       ;\
    and     alu_reg_t2, alu_reg_t2, alu_reg_add_m64                         ;\
    a       alu_reg_t0, alu_reg_t0, alu_reg_t2                              ;\
    shufb          ret, alu_reg_t0, alu_reg_t0, alu_reg_se64                ;

#define add_128(ret, lhs, rhs)                                               \
    cg      alu_reg_t1, lhs, rhs                                            ;\
    a       alu_reg_t0, lhs, rhs                                            ;\
    shlqbyi alu_reg_t1, alu_reg_t1, 4                                       ;\
    cg      alu_reg_t2, alu_reg_t0, alu_reg_t1                              ;\
    a       alu_reg_t0, alu_reg_t0, alu_reg_t1                              ;\
    shlqbyi alu_reg_t2, alu_reg_t2, 4                                       ;\
    cg      alu_reg_t1, alu_reg_t0, alu_reg_t2                              ;\
    a       alu_reg_t0, alu_reg_t0, alu_reg_t2                              ;\
    shlqbyi alu_reg_t1, alu_reg_t1, 4                                       ;\
    a              ret, alu_reg_t0, alu_reg_t1                              ;

#define mul_64(ret, lhs, rhs)                                                \
    shufb   alu_reg_i0, lhs, lhs, alu_reg_mul_lhs                           ;\
    shufb   alu_reg_i1, rhs, rhs, alu_reg_mul_rhs                           ;\
    shli    alu_reg_v0, alu_reg_i0, 16                                      ;\
    shli    alu_reg_v1, alu_reg_i1, 16                                      ;\
    mpyu    alu_reg_t0, alu_reg_i0, alu_reg_i1                              ;\
    mpyhhu  alu_reg_t1, alu_reg_i0, alu_reg_v1                              ;\
    mpyhhu  alu_reg_t2, alu_reg_i1, alu_reg_v0                              ;\
    mpyhhu  alu_reg_t3, alu_reg_i0, alu_reg_i1                              ;\
    shufb   alu_reg_v0, alu_reg_t0, alu_reg_t0, alu_reg_mul_m0              ;\
    shufb   alu_reg_v1, alu_reg_t3, alu_reg_t3, alu_reg_mul_m1              ;\
    shufb   alu_reg_v2, alu_reg_t0, alu_reg_t3, alu_reg_mul_m2              ;\
    shufb   alu_reg_v3, alu_reg_t1, alu_reg_t1, alu_reg_mul_m3              ;\
    shufb   alu_reg_v4, alu_reg_t2, alu_reg_t2, alu_reg_mul_m3              ;\
    shufb   alu_reg_v5, alu_reg_t1, alu_reg_t1, alu_reg_mul_m4              ;\
    shufb   alu_reg_v6, alu_reg_t2, alu_reg_t2, alu_reg_mul_m4              ;\
    add_128(alu_reg_v0, alu_reg_v0, alu_reg_v1)                             ;\
    add_128(alu_reg_v2, alu_reg_v2, alu_reg_v3)                             ;\
    add_128(alu_reg_v4, alu_reg_v4, alu_reg_v5)                             ;\
    add_128(alu_reg_v0, alu_reg_v0, alu_reg_v2)                             ;\
    add_128(alu_reg_v0, alu_reg_v0, alu_reg_v4)                             ;\
    add_128(alu_reg_v0, alu_reg_v0, alu_reg_v6)                             ;\
    shufb          ret, alu_reg_v0, alu_reg_v0, alu_reg_se64                ;

// Functions

    .global alu_constants_init
    .type   alu_constants_init, @function
alu_constants_init:
    ila   alu_reg_t0, alu_endian
    lqd   alu_reg_se32,    0x00(alu_reg_t0)
    lqd   alu_reg_se64,    0x10(alu_reg_t0)
    lqd   alu_reg_se128,   0x20(alu_reg_t0)
    ila   alu_reg_t0, alu_wswap
    lqd   alu_reg_mul_lhs, 0x00(alu_reg_t0)
    lqd   alu_reg_mul_rhs, 0x10(alu_reg_t0)
    ila   alu_reg_t0, alu_mul64_constants
    lqd   alu_reg_mul_m0,  0x00(alu_reg_t0)
    lqd   alu_reg_mul_m1,  0x10(alu_reg_t0)
    lqd   alu_reg_mul_m2,  0x20(alu_reg_t0)
    lqd   alu_reg_mul_m3,  0x30(alu_reg_t0)
    lqd   alu_reg_mul_m4,  0x40(alu_reg_t0)
    ila   alu_reg_t0, alu_add64_constants
    lqd   alu_reg_add_m64, 0x00(alu_reg_t0)
    bi    $lr
