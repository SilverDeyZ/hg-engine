.nds
.thumb

// included by armips/global.s

// IMPLEMENT_HM_BADGE_CONFIG — Layer A execution gate.
//
// Patches the badge immediate byte inside each vanilla FieldMove_CheckXxx function.
// Each function loads its required badge via "MOVS r1, #badge" before calling
// PlayerProfile_TestBadgeFlag. Patching that byte changes which badge is checked.
//
// Encoding: MOVS r1, #N is stored as bytes [N, 0x21] in Thumb. Only byte 0 (N) is patched.
//
// Addresses verified via pret/pokeheartgold/src/field_move.c + arm9 binary scan.
// When IMPLEMENT_HM_BADGE_CONFIG == 0, vanilla bytes are written — no behavior change.
//
// To enable: set IMPLEMENT_HM_BADGE_CONFIG equ 1 in armips/include/config.s and
// #define IMPLEMENT_HM_BADGE_CONFIG in include/config.h (and set desired badge values).

.open "base/arm9.bin", 0x02000000

.if IMPLEMENT_HM_BADGE_CONFIG == 1

// HM01 Cut — FieldMove_CheckCut, function at 0x02067F68
// badge immediate at 0x02067F80 (MOVS r1, #badge)
.org 0x02067F80
.byte HM01_CUT_BADGE

// HM02 Fly — FieldMove_CheckFly, function at 0x0206800C
// badge immediate at 0x02068024
.org 0x02068024
.byte HM02_FLY_BADGE

// HM03 Surf — FieldMove_CheckSurf, function at 0x020680E0
// badge immediate at 0x020680F8
.org 0x020680F8
.byte HM03_SURF_BADGE

// HM04 Strength — FieldMove_CheckStrength, function at 0x020681C0
// badge immediate at 0x020681D8
.org 0x020681D8
.byte HM04_STRENGTH_BADGE

// HM06 Rock Smash — FieldMove_CheckRockSmash, function at 0x02068270
// badge immediate at 0x02068288
.org 0x02068288
.byte HM06_ROCK_SMASH_BADGE

// HM07 Waterfall — FieldMove_CheckWaterfall, function at 0x02068318
// badge immediate at 0x02068340
// Note: vanilla also requires player to be surfing before badge is checked.
.org 0x02068340
.byte HM07_WATERFALL_BADGE

// HM08 Rock Climb — FieldMove_CheckRockClimb, function at 0x020683D0
// badge immediate at 0x020683E8
// This is the same byte that .context/rock_climb.s was patching.
.org 0x020683E8
.byte HM08_ROCK_CLIMB_BADGE

// HM05 Whirlpool — FieldMove_CheckWhirlpool, function at 0x0206885C
// badge immediate at 0x02068884
// Note: vanilla also requires player to be surfing before badge is checked.
// fieldMoveIndex = 12 (function is at a higher address than the other 7 HMs).
.org 0x02068884
.byte HM05_WHIRLPOOL_BADGE

.endif

.close
