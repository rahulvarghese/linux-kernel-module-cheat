/* https://github.com/cirosantilli/linux-kernel-module-cheat#lkmc-c */

#ifndef LKMC_H
#define LKMC_H

/* Common C definitions. */
#if !defined(__ASSEMBLER__)
#include <inttypes.h>
#include <stdbool.h>
#include <stdlib.h>

void lkmc_assert(bool);
void lkmc_assert_fail();
bool lkmc_vector_equal(size_t n, double *v1, double *v2, double max_err);
#endif

/* https://stackoverflow.com/questions/1489932/how-to-concatenate-twice-with-the-c-preprocessor-and-expand-a-macro-as-in-arg */
#define LKMC_CONCAT_EVAL(a,b) a ## b
#define LKMC_CONCAT(a,b) LKMC_CONCAT_EVAL(a, b)

#define LKMC_GLOBAL(name) \
    .global name; \
    name:

/* Weak means that if any other file defines it as a non-weak global,
 * that one will take precedence:
 * https://stackoverflow.com/questions/274753/how-to-make-weak-linking-work-with-gcc/54601464#54601464
 */
#define LKMC_WEAK(name) \
    .weak name; \
    name:

/* aarch64 specifics. */
#if defined(__aarch64__)

/* LKMC_VECTOR_TABLE
 *
 * Adapted from: https://github.com/takeharukato/sample-tsk-sw/blob/ce7973aa5d46c9eedb58309de43df3b09d4f8d8d/hal/aarch64/vector.S
 */

#define LKMC_VECTOR_SYNC_SP0     (0x1)
#define LKMC_VECTOR_IRQ_SP0      (0x2)
#define LKMC_VECTOR_FIQ_SP0      (0x3)
#define LKMC_VECTOR_SERR_SP0     (0x4)

#define LKMC_VECTOR_SYNC_SPX     (0x11)
#define LKMC_VECTOR_IRQ_SPX      (0x12)
#define LKMC_VECTOR_FIQ_SPX      (0x13)
#define LKMC_VECTOR_SERR_SPX     (0x14)

#define LKMC_VECTOR_SYNC_AARCH64 (0x21)
#define LKMC_VECTOR_IRQ_AARCH64  (0x22)
#define LKMC_VECTOR_FIQ_AARCH64  (0x23)
#define LKMC_VECTOR_SERR_AARCH64 (0x24)

#define LKMC_VECTOR_SYNC_AARCH32 (0x31)
#define LKMC_VECTOR_IRQ_AARCH32  (0x32)
#define LKMC_VECTOR_FIQ_AARCH32  (0x33)
#define LKMC_VECTOR_SERR_AARCH32 (0x34)

#define LKMC_VECTOR_EXC_FRAME_SIZE      (288) /* sizeof(lkmc_vector_exception_frame)             */
#define LKMC_VECTOR_EXC_EXC_TYPE_OFFSET (0)   /* offsetof(lkmc_vector_exception_frame, exc_type) */
#define LKMC_VECTOR_EXC_EXC_ESR_OFFSE   (8)   /* offsetof(lkmc_vector_exception_frame, exc_esr)  */
#define LKMC_VECTOR_EXC_EXC_SP_OFFSET   (16)  /* offsetof(lkmc_vector_exception_frame, exc_sp)   */
#define LKMC_VECTOR_EXC_EXC_ELR_OFFSET  (24)  /* offsetof(lkmc_vector_exception_frame, exc_elr)  */
#define LKMC_VECTOR_EXC_EXC_SPSR_OFFSET (32)  /* offsetof(lkmc_vector_exception_frame, exc_spsr) */

#define LKMC_VECTOR_FUNC_ALIGN .align 2
#define LKMC_VECTOR_SYMBOL_PREFIX lkmc_vector_

#define LKMC_VECTOR_BUILD_TRAPFRAME(exc_type) \
    stp x29, x30, [sp, -16]!; \
    stp x27, x28, [sp, -16]!; \
    stp x25, x26, [sp, -16]!; \
    stp x23, x24, [sp, -16]!; \
    stp x21, x22, [sp, -16]!; \
    stp x19, x20, [sp, -16]!; \
    stp x17, x18, [sp, -16]!; \
    stp x15, x16, [sp, -16]!; \
    stp x13, x14, [sp, -16]!; \
    stp x11, x12, [sp, -16]!; \
    stp x9, x10, [sp, -16]!; \
    stp x7, x8, [sp, -16]!; \
    stp x5, x6, [sp, -16]!; \
    stp x3, x4, [sp, -16]!; \
    stp x1, x2, [sp, -16]!; \
    mrs x21, spsr_el1; \
    stp x21, x0, [sp, -16]!; \
    mrs x21, elr_el1; \
    stp xzr, x21, [sp, -16]!; \
    mov x21, exc_type; \
    mrs x22, esr_el1; \
    stp x21, x22, [sp, -16]!

#define LKMC_VECTOR_STORE_TRAPED_SP \
    mrs x21, sp_el0; \
    str x21, [sp, LKMC_VECTOR_EXC_EXC_SP_OFFSET]

#define LKMC_VECTOR_CALL_TRAP_HANDLER \
    mov x0, sp; \
    bl lkmc_vector_trap_handler

#define LKMC_VECTOR_STORE_NESTED_SP \
    mov x21, sp; \
    add x21, x21, LKMC_VECTOR_EXC_FRAME_SIZE; \
    str x21, [sp, LKMC_VECTOR_EXC_EXC_SP_OFFSET]

#define LKMC_VECTOR_RESTORE_TRAPED_SP \
    ldr x21, [sp, LKMC_VECTOR_EXC_EXC_SP_OFFSET]; \
    msr sp_el0, x21

#define LKMC_VECTOR_RESTORE_TRAPFRAME \
    add sp, sp, 16; \
    ldp x21, x22, [sp], 16; \
    msr elr_el1, x22; \
    ldp x21, x0, [sp], 16; \
    msr spsr_el1, x21; \
    ldp x1, x2, [sp], 16; \
    ldp x3, x4, [sp], 16; \
    ldp x5, x6, [sp], 16; \
    ldp x7, x8, [sp], 16; \
    ldp x9, x10, [sp], 16; \
    ldp x11, x12, [sp], 16; \
    ldp x13, x14, [sp], 16; \
    ldp x15, x16, [sp], 16; \
    ldp x17, x18, [sp], 16; \
    ldp x19, x20, [sp], 16; \
    ldp x21, x22, [sp], 16; \
    ldp x23, x24, [sp], 16; \
    ldp x25, x26, [sp], 16; \
    ldp x27, x28, [sp], 16; \
    ldp x29, x30, [sp], 16; \
    eret

#define LKMC_VECTOR_ENTRY(func_name) \
    .align 7; \
    b LKMC_VECTOR_SYMBOL_PREFIX ## func_name

#define LKMC_VECTOR_FUNC(func_name, func_id) \
    LKMC_VECTOR_FUNC_ALIGN; \
LKMC_VECTOR_SYMBOL_PREFIX ## func_name:; \
    LKMC_VECTOR_BUILD_TRAPFRAME(func_id); \
    LKMC_VECTOR_STORE_TRAPED_SP; \
    LKMC_VECTOR_CALL_TRAP_HANDLER; \
    LKMC_VECTOR_RESTORE_TRAPED_SP; \
    LKMC_VECTOR_RESTORE_TRAPFRAME

#define LKMC_VECTOR_FUNC_NESTED(func_name, func_id) \
    LKMC_VECTOR_FUNC_ALIGN; \
LKMC_VECTOR_SYMBOL_PREFIX ## func_name:; \
    LKMC_VECTOR_BUILD_TRAPFRAME(func_id); \
    LKMC_VECTOR_STORE_NESTED_SP; \
    LKMC_VECTOR_CALL_TRAP_HANDLER; \
    LKMC_VECTOR_RESTORE_TRAPFRAME

/* Define the actual vector table. */
#define LKMC_VECTOR_TABLE \
    .align 11; \
    LKMC_GLOBAL(lkmc_vector_table); \
    ; \
    LKMC_VECTOR_ENTRY(curr_el_sp0_sync); \
    LKMC_VECTOR_ENTRY(curr_el_sp0_irq); \
    LKMC_VECTOR_ENTRY(curr_el_sp0_fiq); \
    LKMC_VECTOR_ENTRY(curr_el_sp0_serror); \
    ; \
    LKMC_VECTOR_ENTRY(curr_el_spx_sync); \
    LKMC_VECTOR_ENTRY(curr_el_spx_irq); \
    LKMC_VECTOR_ENTRY(curr_el_spx_fiq); \
    LKMC_VECTOR_ENTRY(curr_el_spx_serror); \
    ; \
    LKMC_VECTOR_ENTRY(lower_el_aarch64_sync); \
    LKMC_VECTOR_ENTRY(lower_el_aarch64_irq); \
    LKMC_VECTOR_ENTRY(lower_el_aarch64_fiq); \
    LKMC_VECTOR_ENTRY(lower_el_aarch64_serror); \
    ; \
    LKMC_VECTOR_ENTRY(lower_el_aarch32_sync); \
    LKMC_VECTOR_ENTRY(lower_el_aarch32_irq); \
    LKMC_VECTOR_ENTRY(lower_el_aarch32_fiq); \
    LKMC_VECTOR_ENTRY(lower_el_aarch32_serror); \
    ; \
    LKMC_VECTOR_FUNC(curr_el_sp0_sync, LKMC_VECTOR_SYNC_SP0); \
    LKMC_VECTOR_FUNC(curr_el_sp0_irq, LKMC_VECTOR_IRQ_SP0); \
    LKMC_VECTOR_FUNC(curr_el_sp0_fiq, LKMC_VECTOR_FIQ_SP0); \
    LKMC_VECTOR_FUNC(curr_el_sp0_serror, LKMC_VECTOR_SERR_SP0); \
    ; \
    LKMC_VECTOR_FUNC_NESTED(curr_el_spx_sync, LKMC_VECTOR_SYNC_SPX); \
    LKMC_VECTOR_FUNC_NESTED(curr_el_spx_irq, LKMC_VECTOR_IRQ_SPX); \
    LKMC_VECTOR_FUNC_NESTED(curr_el_spx_fiq, LKMC_VECTOR_FIQ_SPX); \
    LKMC_VECTOR_FUNC_NESTED(curr_el_spx_serror, LKMC_VECTOR_SERR_SPX); \
    ; \
    LKMC_VECTOR_FUNC(lower_el_aarch64_sync, LKMC_VECTOR_SYNC_AARCH64); \
    LKMC_VECTOR_FUNC(lower_el_aarch64_irq, LKMC_VECTOR_IRQ_AARCH64); \
    LKMC_VECTOR_FUNC(lower_el_aarch64_fiq, LKMC_VECTOR_FIQ_AARCH64); \
    LKMC_VECTOR_FUNC(lower_el_aarch64_serror, LKMC_VECTOR_SERR_AARCH64); \
    ; \
    LKMC_VECTOR_FUNC(lower_el_aarch32_sync, LKMC_VECTOR_SYNC_AARCH32); \
    LKMC_VECTOR_FUNC(lower_el_aarch32_irq, LKMC_VECTOR_IRQ_AARCH32); \
    LKMC_VECTOR_FUNC(lower_el_aarch32_fiq, LKMC_VECTOR_FIQ_AARCH32); \
    LKMC_VECTOR_FUNC(lower_el_aarch32_serror, LKMC_VECTOR_SERR_AARCH32)

/* aarch64 C definitions. */
#if !defined(__ASSEMBLER__)
#include <stdint.h>

typedef struct {
    uint64_t exc_type;
    uint64_t exc_esr;
    uint64_t exc_sp;
    uint64_t exc_elr;
    uint64_t exc_spsr;
    uint64_t x0;
    uint64_t x1;
    uint64_t x2;
    uint64_t x3;
    uint64_t x4;
    uint64_t x5;
    uint64_t x6;
    uint64_t x7;
    uint64_t x8;
    uint64_t x9;
    uint64_t x10;
    uint64_t x11;
    uint64_t x12;
    uint64_t x13;
    uint64_t x14;
    uint64_t x15;
    uint64_t x16;
    uint64_t x17;
    uint64_t x18;
    uint64_t x19;
    uint64_t x20;
    uint64_t x21;
    uint64_t x22;
    uint64_t x23;
    uint64_t x24;
    uint64_t x25;
    uint64_t x26;
    uint64_t x27;
    uint64_t x28;
    uint64_t x29;
    uint64_t x30;
} LkmcVectorExceptionFrame;

void lkmc_vector_trap_handler(LkmcVectorExceptionFrame *exception);

#define LKMC_SVC(immediate) __asm__ __volatile__("svc " #immediate : : : )

#define LKMC_SYSREG_SYMBOL_PREFIX lkmc_sysreg_
#define LKMC_SYSREG_READ_WRITE(type, name) \
    type LKMC_CONCAT(LKMC_CONCAT(LKMC_SYSREG_SYMBOL_PREFIX, name), _read)(void); \
    void LKMC_CONCAT(LKMC_CONCAT(LKMC_SYSREG_SYMBOL_PREFIX, name), _write)(type name);
#define LKMC_SYSREG_OPS \
    LKMC_SYSREG_READ_WRITE(uint32_t, cntv_ctl_el0) \
    LKMC_SYSREG_READ_WRITE(uint32_t, daif) \
    LKMC_SYSREG_READ_WRITE(uint32_t, spsel) \
    LKMC_SYSREG_READ_WRITE(uint64_t, cntfrq_el0) \
    LKMC_SYSREG_READ_WRITE(uint64_t, cntv_cval_el0) \
    LKMC_SYSREG_READ_WRITE(uint64_t, cntv_tval_el0) \
    LKMC_SYSREG_READ_WRITE(uint64_t, cntvct_el0) \
    LKMC_SYSREG_READ_WRITE(uint64_t, sp_el1) \
    LKMC_SYSREG_READ_WRITE(uint64_t, vbar_el1)
LKMC_SYSREG_OPS
#undef LKMC_SYSREG_READ_WRITE

#endif
#endif
#endif
