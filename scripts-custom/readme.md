Anytime Phone Rematch — How It Works

  The Problem With Vanilla

  Vanilla HGSS gates phone rematches behind three separate checks:
  1. FLAG_BEAT_RADIO_TOWER_ROCKETS — must have cleared the Radio Tower
  2. Weekday + time-of-day — each trainer only calls on a specific day/time window
  3. RNG — even when all conditions pass, a percentage roll can still reject the call

  Gym leaders add a fourth gate: 16 total badges (all Johto + all Kanto).

  What Was Hooked

  Four functions in overlay_101 were replaced:

  ┌──────────────────────────────────────────────────────────────┬────────────┬────────────────────┐
  │                         Hook target                          │  Address   │      Purpose       │
  ├──────────────────────────────────────────────────────────────┼────────────┼────────────────────┤
  │                                                              │            │ Gate: "should this │
  │ PhoneScript_Generic_NoRematchUntilClearedRadioTower          │ 0x021F2CB8 │  trainer offer a   │
  │                                                              │            │ rematch right      │
  │                                                              │            │ now?"              │
  ├──────────────────────────────────────────────────────────────┼────────────┼────────────────────┤
  │ PhoneScript_Generic_RematchAfterRadioTowerSpecificDayAndTime │ 0x021F2D10 │ Same gate,         │
  │                                                              │            │ day/time variant   │
  ├──────────────────────────────────────────────────────────────┼────────────┼────────────────────┤
  │                                                              │            │ Dialogue: "I'm     │
  │ PhoneScript_Generic_RematchAfterRadioTowerExceptBugContest   │ 0x021F2D48 │ still waiting for  │
  │                                                              │            │ our battle"        │
  ├──────────────────────────────────────────────────────────────┼────────────┼────────────────────┤
  │ PhoneCall_GetScriptId_GymLeader                              │ 0x021F3EA8 │ Gym leader call    │
  │                                                              │            │ setup              │
  └──────────────────────────────────────────────────────────────┴────────────┴────────────────────┘

  Regular Trainers

  PhoneRematch_GenericActivationGate replaces both activation gate functions. Logic:

  if IsSeeking(caller) → FALSE   ← already scheduled, prevent double-booking
  if johtoBadges < threshold → FALSE
  else → TRUE                    ← always accept, no RNG, no day/time check

  PhoneRematch_AlreadySeekingDialogue replaces the "still waiting" dialogue function:
  if johtoBadges < threshold → FALSE
  if IsSeeking(caller) → TRUE    ← show "I'm still waiting" dialogue

  The badge threshold is PHONE_REMATCH_BADGE_THRESHOLD (default: 3) in config.h.

  Gym Leaders

  The gym leader path is more complex because their call uses a state machine
  (GearPhoneCall_GymLeader_Outgoing) that reads two flags and also checks the phone book entry's
  expected weekday/time.

  PhoneRematch_GetScriptId_GymLeader runs before that state machine and sets it up:

  1. flag0 (badge gate): set to 1 if totalBadges >= GYM_LEADER_REMATCH_BADGE_THRESHOLD (default: 16) —
   the state machine reads this to decide whether to say "not enough badges" or offer a battle
  2. flag1 (seeking): set to 1 if IsSeeking — the state machine uses this for "already waiting"
  dialogue
  3. Weekday/time bypass: the phone book entry's rematchWeekday and rematchTimeOfDay fields are
  overwritten with the current values, so the state machine's day/time comparison always passes

  The phone book entry is in overlay RAM, so modifying it is safe — it resets the next time the
  overlay loads.

  Config Knobs

  // config.h
  #define IMPLEMENT_ANYTIME_PHONE_REMATCH        // master toggle
  #define PHONE_REMATCH_BADGE_THRESHOLD     3    // regular trainers
  #define GYM_LEADER_REMATCH_BADGE_THRESHOLD 16  // gym leaders

  Disabling requires removing the #define and commenting out the four hooks entries (the hook stubs
  always return FALSE when the feature is off, which blocks rematches entirely rather than restoring
  vanilla behavior)