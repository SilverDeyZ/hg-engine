.text
.thumb
.align 2

.extern SetOverworldRequestFlags
.extern CheckOverworldRequestFlags

// SetOverworldRequestFlags_hook
// Hook register 0 (uses r0) at 0x021E6982.
// At this point: r5 = OVERWORLD_REQUEST_FLAGS*, [sp+0] = trg (current frame buttons).
// Writes 10 bytes (2-byte aligned), displacing 3 halfword instructions:
//   ldr r0, [sp, #4]  ;  cmp r0, #0  ;  beq .L_no_icon0
.global SetOverworldRequestFlags_hook
.type SetOverworldRequestFlags_hook, %function
SetOverworldRequestFlags_hook:
    mov  r0, r5             @ arg0 = req
    ldr  r1, [sp]           @ arg1 = trg
    bl   SetOverworldRequestFlags

    @ Replicate displaced vanilla code
    ldr  r0, [sp, #4]       @ icon0received
    cmp  r0, #0
    beq  .Lno_icon0
    mov  r1, #2
    ldr  r0, [sp]           @ trg
    ldr  r2, =0x021E698D    @ resume at "icon0 received" path (0x021E698C | 1)
    bx   r2

.Lno_icon0:
    ldr  r0, =0x021E6993    @ resume at "no icon0" path (0x021E6992 | 1)
    bx   r0


// CheckOverworldRequestFlags_hook
// Hook register 3 (uses r3) at 0x021E6AF6.
// At entry: r0 = OVERWORLD_REQUEST_FLAGS*, r1 = FieldSystem* (vanilla function args).
// Vanilla prologue displaced: mov r5, r0; ldrh r0, [r5]; mov r4, r1; lsl r0, r0, #0x12; lsr r0, r0, #0x1f
// Hook at 0x021E6AF6 (4-byte aligned) displaces 4 bytes: mov r5, r0; ldrh r0, [r5]
.global CheckOverworldRequestFlags_hook
.type CheckOverworldRequestFlags_hook, %function
CheckOverworldRequestFlags_hook:
    push {r0-r7}
    bl   CheckOverworldRequestFlags  @ called with r0=req, r1=fsys
    pop  {r0-r7}

    @ Replicate displaced vanilla prologue
    mov  r5, r0             @ r5 = OVERWORLD_REQUEST_FLAGS*
    ldrh r0, [r5]
    mov  r4, r1             @ r4 = FieldSystem*
    lsl  r0, r0, #0x12      @ isolate TalkCheck bit
    lsr  r0, r0, #0x1f
    bne  .LtalkCheck
    ldr  r2, =0x021E6B03    @ resume at "no TalkCheck" path (0x021E6B02 | 1)
    bx   r2

.LtalkCheck:
    ldr  r0, =0x021E6B13    @ resume at "TalkCheck set" path (0x021E6B12 | 1)
    bx   r0
