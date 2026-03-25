#ifndef PHONE_REMATCH_H
#define PHONE_REMATCH_H

#include "types.h"
#include "save.h"

/*
 * Minimal partial struct of PokegearPhoneCallContext (pret/pokeheartgold: phone_internal.h).
 *
 * Only the three fields accessed by phone_rematch.c are exposed by name.
 * All other members are covered by opaque padding arrays of verified size.
 * Offsets confirmed via overlay_101 disassembly.
 *
 * Full struct context_offset map (PokegearPhoneCallContext):
 *   0x20 — callPersistentState (PhoneCallPersistentState *)
 *   0x24 — playerProfile       (PlayerProfile *)
 *   0xA0 — state.callerID      (u8)  — PokegearPhoneCallState at 0x88, callerID at +0x18
 *   0xA1 — state.isIncomingCall (u8) — PokegearPhoneCallState at 0x88, isIncomingCall at +0x19
 */
typedef struct PhoneRematchCtx {
    u8                    _pad_00[0x20];
    void                 *callPersistentState;  /* 0x20 — PhoneCallPersistentState * */
    struct PlayerProfile *playerProfile;        /* 0x24 */
    u8                    _pad_28[0x78];        /* 0x28–0x9F */
    u8                    callerID;             /* 0xA0 — state.callerID */
    u8                    isIncomingCall;       /* 0xA1 — state.isIncomingCall */
} PhoneRematchCtx;

/*
 * Minimal partial struct of PokegearPhoneCallState (pret/pokeheartgold: phone_internal.h).
 *
 * Used only by PhoneRematch_GetScriptId_GymLeader, which receives this as arg1.
 * Offsets confirmed via overlay_101 disassembly of PhoneCall_GetScriptId_GymLeader.
 *
 * Full struct offset map (PokegearPhoneCallState):
 *   0x10 — phoneBookEntry   (PhoneBookEntry *)
 *   0x18 — callerID         (u8)
 *   0x19 — isIncomingCall   (u8)
 *   0x20 — scriptType       (u16)
 *   0x23 — timeOfDay        (u8)
 *   0x34 — date.week        (enum RTCWeek = u32) — RTCDate at 0x28, week at +0x0C
 *   0x4D — flags byte       (bit0=flag0/badge_ok, bit1=flag1/seeking)
 */
typedef struct PhoneRematchCallState {
    u8   _pad_00[0x10];
    void *phoneBookEntry;   /* 0x10 — PhoneBookEntry * */
    u8   _pad_14[0x04];
    u8   callerID;          /* 0x18 */
    u8   isIncomingCall;    /* 0x19 */
    u8   _pad_1A[0x06];
    u16  scriptType;        /* 0x20 */
    u8   _pad_22;           /* 0x22 */
    u8   timeOfDay;         /* 0x23 */
    u8   _pad_24[0x10];     /* 0x24–0x33: hangupToneTimer + RTCDate.year/month/day */
    u32  dateWeek;          /* 0x34 — RTCDate.week (enum RTCWeek) */
    u8   _pad_38[0x15];     /* 0x38–0x4C: RTCTime + misc save fields */
    u8   flags;             /* 0x4D — bit0=flag0 (badge gate), bit1=flag1 (seeking) */
} PhoneRematchCallState;

/*
 * Minimal partial struct of PhoneScriptGenericHeader (pret/pokeheartgold: phone_internal.h).
 * Describes one entry in a trainer's generic phone call script table.
 */
typedef struct PhoneScriptGenericHeader {
    u8  type;       /* 0x00 — PHONECALLGENERIC_* constant */
    u8  chance;     /* 0x01 — 0–100 percent chance for vanilla RNG gate */
    u16 scriptType; /* 0x02 */
    u16 scriptID;   /* 0x04 */
} PhoneScriptGenericHeader;

/*
 * Minimal partial struct of PhoneBookEntry (pret/pokeheartgold: gear_phone.h).
 * Only the rematch scheduling fields are exposed.
 * Used to force the day/time check in GearPhoneCall_GymLeader_Outgoing to pass.
 */
typedef struct PhoneBookEntryMinimal {
    u8 _pad_00[0x0D];
    u8 rematchWeekday;    /* 0x0D — expected weekday for gym leader outgoing call */
    u8 rematchTimeOfDay;  /* 0x0E — expected time of day for gym leader outgoing call */
} PhoneBookEntryMinimal;

/*
 * PhoneCallPersistentState_PhoneRematches_IsSeeking
 *
 * Returns TRUE if trainer `idx` already has a pending rematch scheduled
 * (seeking flag is set in the persistent phone call state).
 *
 * Address: 0x0202F0E8 (ARM9, Thumb).
 * Confirmed from overlay_101 BL trace at 0x021F2CC6 and 0x021F3EDC.
 *
 * state — pointer to PhoneCallPersistentState (passed as void* to avoid
 *          importing the full type; only the address is used by the ROM).
 * idx   — trainer's phone book callerID.
 */
BOOL LONG_CALL PhoneCallPersistentState_PhoneRematches_IsSeeking(void *state, u8 idx);

/* Hook replacement functions — registered in hooks file for overlay 0101. */
BOOL PhoneRematch_GenericActivationGate(PhoneRematchCtx *ctx, PhoneScriptGenericHeader *hdr);
BOOL PhoneRematch_AlreadySeekingDialogue(PhoneRematchCtx *ctx, PhoneScriptGenericHeader *hdr);
u16  PhoneRematch_GetScriptId_GymLeader(PhoneRematchCtx *ctx, PhoneRematchCallState *state);

#endif /* PHONE_REMATCH_H */
