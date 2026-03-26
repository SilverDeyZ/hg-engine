.nds
.thumb

/*
 * Radio Sound Encounter Patches (overlay_101 + ARM9)
 *
 * Changes from vanilla behavior:
 *   1. All 7 weekdays now route to either Hoenn Sound (Mon/Wed/Fri) or
 *      Sinnoh Sound (Sun/Tue/Thu/Sat) — no day plays March or Lullaby.
 *   2. National Dex requirement removed for both Hoenn and Sinnoh Sound.
 *   3. Returning from battle no longer clears the active radio sequence,
 *      so sound encounter slots remain active across encounters.
 *
 * Overlay 101 base address: 0x021E7740
 * ARM9 base address:        0x02000000
 */

/* ------------------------------------------------------------------ */
/* overlay_101 — RadioShow_PokemonMusic_Setup() weekday branch table   */
/* ------------------------------------------------------------------ */
/*
 * 7-entry Thumb branch-offset jump table at 0x021F5F9A.
 * Each halfword is added to PC (= 0x021F5F9C) to reach the case handler.
 * Vanilla entries: Sun/Mon/Fri → March, Tue/Sat → Lullaby, Wed → Hoenn,
 *   Thu → Sinnoh.
 *
 * Offsets:
 *   0x0036 → Wednesday case (Hoenn Sound / PKMUSTRACK_HOENN = 2)
 *   0x0054 → Thursday case  (Sinnoh Sound / PKMUSTRACK_SINNOH = 3)
 *
 * New split (alternating, preserving original Wed/Thu anchors):
 *   Sun → Sinnoh, Mon → Hoenn, Tue → Sinnoh, Wed → Hoenn (orig),
 *   Thu → Sinnoh (orig), Fri → Hoenn, Sat → Sinnoh
 */

.open "base/overlay/overlay_0101.bin", 0x021E7740

.org 0x021F5F9A
.halfword 0x0054 // Sunday    → Sinnoh Sound
.halfword 0x0036 // Monday    → Hoenn Sound
.halfword 0x0054 // Tuesday   → Sinnoh Sound
.halfword 0x0036 // Wednesday → Hoenn Sound (original)
.halfword 0x0054 // Thursday  → Sinnoh Sound (original)
.halfword 0x0036 // Friday    → Hoenn Sound
.halfword 0x0054 // Saturday  → Sinnoh Sound

/* ------------------------------------------------------------------ */
/* overlay_101 — Remove National Dex requirement for Hoenn Sound       */
/* ------------------------------------------------------------------ */
/*
 * Wednesday branch, no-Dex fallback path.
 * Vanilla: MOVS r0, #0 (PKMUSTRACK_MARCH). Patch: #2 (PKMUSTRACK_HOENN).
 * Address: 0x021F5FE4, file offset 0xe8a4.
 */

.org 0x021F5FE4
.byte 0x02 // PKMUSTRACK_HOENN — was 0x00 (PKMUSTRACK_MARCH)

/* ------------------------------------------------------------------ */
/* overlay_101 — Remove National Dex requirement for Sinnoh Sound      */
/* ------------------------------------------------------------------ */
/*
 * Thursday branch, no-Dex fallback path.
 * Vanilla: MOVS r0, #1 (PKMUSTRACK_LULLABY). Patch: #3 (PKMUSTRACK_SINNOH).
 * Address: 0x021F6002, file offset 0xe8c2.
 */

.org 0x021F6002
.byte 0x03 // PKMUSTRACK_SINNOH — was 0x01 (PKMUSTRACK_LULLABY)

.close

/* ------------------------------------------------------------------ */
/* ARM9 — Keep radio active after battle / field BGM restore           */
/* ------------------------------------------------------------------ */
/*
 * sub_02005DF4 (0x02005DF4) restores field BGM after battle and
 * unconditionally calls SndRadio_StopSeq(0), clearing sRadioSeqNo.
 * This prevents sound encounter slots from persisting across battles.
 *
 * The call sequence is:
 *   0x02005E20: MOVS r0, #0
 *   0x02005E22: BL   SndRadio_StopSeq   ← replaced with two NOPs
 *
 * Replacing the BL with MOV r8,r8 (0x46C0) × 2 skips the stop while
 * leaving r0 unchanged (harmless; next instruction is LDRH r0,[r4]).
 *
 * The explicit radio stop in sub_02005EEC (called from StopBGM) is
 * preserved, so manually closing the Pokegear still clears the sequence.
 */

.open "base/arm9.bin", 0x02000000

.org 0x02005E22
.halfword 0x46C0, 0x46C0 // NOP, NOP — was: BL SndRadio_StopSeq

.close
