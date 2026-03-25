#include "../../include/types.h"
#include "../../include/config.h"
#include "../../include/save.h"
#include "../../include/phone_rematch.h"

/* libgcc (__popcountsi2) is not linked in the overlay build. */
static int count_set_bits_u8(u8 x) {
    x = x - ((x >> 1) & 0x55u);
    x = (x & 0x33u) + ((x >> 2) & 0x33u);
    return (int)((x + (x >> 4)) & 0x0Fu);
}

/*
 * phone_rematch.c — Anytime Phone Rematch system
 *
 * Hooks three functions in overlay_101 to replace the vanilla rematch gating
 * logic with a badge-threshold system. See include/config.h for the design
 * rationale and the feature toggle/threshold values.
 *
 * Hook targets (overlay_101, all Thumb):
 *   PhoneScript_Generic_NoRematchUntilClearedRadioTower    0x021F2CB8
 *   PhoneScript_Generic_RematchAfterRadioTowerSpecific...  0x021F2D10
 *   PhoneScript_Generic_RematchAfterRadioTower...BugContest 0x021F2D48
 *   PhoneCall_GetScriptId_GymLeader                        0x021F3EA8
 *
 * All confirmed against decompressed overlay_0101.bin (load base 0x021E7740).
 * overlay_101 must be in OVERLAYS_TO_DECOMPRESS in scripts/make.py.
 */


/* ------------------------------------------------------------------ */
/* PhoneRematch_GenericActivationGate                                  */
/*                                                                     */
/* Replaces:                                                           */
/*   PhoneScript_Generic_NoRematchUntilClearedRadioTower  (0x021F2CB8) */
/*   PhoneScript_Generic_RematchAfterRadioTowerSpecificDayAndTime      */
/*                                                                     (0x021F2D10) */
/*                                                                     */
/* Returns TRUE to accept a script table entry (offer the rematch),    */
/* or FALSE to skip it and let the caller try the next entry.          */
/*                                                                     */
/* Vanilla logic replaced:                                             */
/*   - if IsSeeking → FALSE (already scheduled; preserved)            */
/*   - if FLAG_BEAT_RADIO_TOWER_ROCKETS not set → FALSE (removed)     */
/*   - specific weekday and time-of-day check → FALSE (removed)       */
/*   - RNG: rollPercentChance(hdr->chance) → replaced with TRUE        */
/*                                                                     */
/* Replacement logic:                                                  */
/*   - if IsSeeking → FALSE (preserve: prevents double-scheduling)     */
/*   - if johtoBadges < PHONE_REMATCH_BADGE_THRESHOLD → FALSE          */
/*   - else TRUE                                                       */
/*                                                                     */
/* Omissions (v1):                                                     */
/*   GiftItemIdGet guard: omitted. SetSeeking is idempotent; offering  */
/*   a rematch when a gift is pending is harmless in practice.         */
/* ------------------------------------------------------------------ */
BOOL PhoneRematch_GenericActivationGate(PhoneRematchCtx *ctx, PhoneScriptGenericHeader *hdr)
{
    (void)hdr;

#ifdef IMPLEMENT_ANYTIME_PHONE_REMATCH
    if (PhoneCallPersistentState_PhoneRematches_IsSeeking(ctx->callPersistentState, ctx->callerID)) {
        return FALSE;
    }
    return count_set_bits_u8(ctx->playerProfile->johtoBadges) >= PHONE_REMATCH_BADGE_THRESHOLD
        ? TRUE : FALSE;
#else
    /* Feature disabled: this gate never passes. Comment hooks entries to
     * restore vanilla behavior for this slot. */
    (void)ctx;
    return FALSE;
#endif
}


/* ------------------------------------------------------------------ */
/* PhoneRematch_AlreadySeekingDialogue                                 */
/*                                                                     */
/* Replaces:                                                           */
/*   PhoneScript_Generic_RematchAfterRadioTowerExcept...BugContest     */
/*                                                                     (0x021F2D48) */
/*                                                                     */
/* This entry fires AFTER the activation gate. It plays the "I'm still */
/* waiting for our battle" dialogue when seeking is already TRUE.      */
/* Returns TRUE only when seeking is active and badge threshold is met. */
/*                                                                     */
/* Vanilla logic replaced:                                             */
/*   - if FLAG_BEAT_RADIO_TOWER_ROCKETS not set → FALSE (removed)     */
/*   - if mapId==NAT_PARK && BugContest active → FALSE (omitted, v1)  */
/*   - if !IsSeeking → FALSE (structural precondition; preserved)      */
/*   - RNG (chance=100) → replaced with unconditional TRUE             */
/*                                                                     */
/* Omissions (v1):                                                     */
/*   Bug Contest exclusion: during Bug Contest, trainers may say       */
/*   "I'm still waiting." This affects dialogue quality only, not      */
/*   rematch activation or schedule correctness.                       */
/* ------------------------------------------------------------------ */
BOOL PhoneRematch_AlreadySeekingDialogue(PhoneRematchCtx *ctx, PhoneScriptGenericHeader *hdr)
{
    (void)hdr;

#ifdef IMPLEMENT_ANYTIME_PHONE_REMATCH
    if (count_set_bits_u8(ctx->playerProfile->johtoBadges) < PHONE_REMATCH_BADGE_THRESHOLD) {
        return FALSE;
    }
    return PhoneCallPersistentState_PhoneRematches_IsSeeking(ctx->callPersistentState, ctx->callerID)
        ? TRUE : FALSE;
#else
    (void)ctx;
    return FALSE;
#endif
}


/* ------------------------------------------------------------------ */
/* PhoneRematch_GetScriptId_GymLeader                                  */
/*                                                                     */
/* Replaces:                                                           */
/*   PhoneCall_GetScriptId_GymLeader (0x021F3EA8)                      */
/*                                                                     */
/* Prepares state for GearPhoneCall_GymLeader_Outgoing, which runs     */
/* as the registered state machine after this function returns.        */
/*                                                                     */
/* state->flag0: badge gate. GearPhoneCall_GymLeader_Outgoing reads    */
/*   this to decide whether to say "not enough badges" or offer battle. */
/* state->flag1: IsSeeking. GearPhoneCall_GymLeader_Outgoing reads     */
/*   this to short-circuit to "already waiting" dialogue.              */
/* state->phoneBookEntry weekday/time fields: forced to match current  */
/*   state values so the weekday/time check in the state machine always */
/*   passes. The entry is in overlay RAM and reset on next overlay load.*/
/* state->scriptType: 14=incoming, 13=outgoing (vanilla convention).   */
/*                                                                     */
/* Vanilla logic replaced:                                             */
/*   - PlayerProfile_CountBadges >= 16 → GYM_LEADER_REMATCH_BADGE_THRESHOLD */
/*   - weekday/time gate in GearPhoneCall_GymLeader_Outgoing bypassed  */
/*     by matching phoneBookEntry fields to current state values.       */
/*                                                                     */
/* When IMPLEMENT_ANYTIME_PHONE_REMATCH is not defined, this function  */
/* replicates vanilla behavior (badge count vs 16, no time bypass).    */
/* ------------------------------------------------------------------ */
u16 PhoneRematch_GetScriptId_GymLeader(PhoneRematchCtx *ctx, PhoneRematchCallState *state)
{
    int totalBadges = count_set_bits_u8(ctx->playerProfile->johtoBadges)
                    + count_set_bits_u8(ctx->playerProfile->kantoBadges);

#ifdef IMPLEMENT_ANYTIME_PHONE_REMATCH
    u8 flag0 = (totalBadges >= GYM_LEADER_REMATCH_BADGE_THRESHOLD) ? 1 : 0;
#else
    u8 flag0 = (totalBadges >= 16) ? 1 : 0;
#endif

    u8 flag1 = PhoneCallPersistentState_PhoneRematches_IsSeeking(
                   ctx->callPersistentState, state->callerID) ? 1 : 0;

    /* Write flag0 and flag1 into the bitfield byte at state+0x4D.
     * Bits 2-3 (flag2, flag3) are preserved. */
    state->flags = (state->flags & ~0x03u) | flag0 | (u8)(flag1 << 1);

#ifdef IMPLEMENT_ANYTIME_PHONE_REMATCH
    /* Bypass the weekday/time gate in GearPhoneCall_GymLeader_Outgoing.
     * Force the phone book entry's expected day/time to match the current
     * call state, so the comparison always passes.
     * Safe to modify: the entry is in overlay RAM, reset on next load. */
    if (state->phoneBookEntry != NULL) {
        PhoneBookEntryMinimal *entry = (PhoneBookEntryMinimal *)state->phoneBookEntry;
        entry->rematchWeekday   = (u8)(state->dateWeek & 0xFFu);
        entry->rematchTimeOfDay = state->timeOfDay;
    }
#endif

    state->scriptType = state->isIncomingCall ? 14 : 13;

    return 0; /* PHONE_SCRIPT_NONE */
}
