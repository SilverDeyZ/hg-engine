// ============================================================
// Mom's gift / shopping table configuration
// Controlled by MOM_GIFT_CONFIG in armips/include/config.s.
//
// HOW IT WORKS
//   After every trainer battle, 25% of the prize money delta is
//   diverted into Mom's savings account.  When the balance changes,
//   the game runs two checks (in order):
//
//   1. Normal gifts — checked first.  Each entry is one-time only,
//      tracked by a save-state bit.  Entries must stay in ascending
//      threshold order; the loop breaks on the first unmet threshold.
//      When triggered: item is enqueued, cost is deducted from savings.
//
//   2. Berry gift — checked only if no normal gift fired.  Triggers
//      each time the balance crosses a new MOM_GIFT_BERRY_THRESHOLD
//      multiple (e.g. every 3000 saved).  One random berry from the
//      berry table is picked and enqueued.
//
//   Queued gifts are collected from the deliveryman NPC in Violet City.
//   The queue holds at most 5 pending gifts.
//
// TO CUSTOMIZE
//   Edit the equ values in the "CONFIGURATION" section below.
//   Item IDs use the constants defined in asm/include/items.inc.
//   MOM_GIFT_BERRY_n_ITEM must be a berry item ID (>= ITEM_CHERI_BERRY).
//   Table sizes (9 normal, 17 berry) are fixed by vanilla ARM9 loop counts.
// ============================================================

// ============================================================
// CONFIGURATION — normal gift table (9 entries, threshold order)
// ============================================================
// Entry 0
MOM_GIFT_NORMAL_0_ITEM      equ ITEM_SUPER_POTION  // vanilla    |  Item mom give
MOM_GIFT_NORMAL_0_THRESHOLD equ 900                // vanilla    |  Mom money to unlock the purshase
MOM_GIFT_NORMAL_0_COST      equ 600                // vanilla    |  cost of the item mom buy

// Entry 1
MOM_GIFT_NORMAL_1_ITEM      equ ITEM_REPEL         // vanilla
MOM_GIFT_NORMAL_1_THRESHOLD equ 4000               // vanilla
MOM_GIFT_NORMAL_1_COST      equ 270                // vanilla

// Entry 2
MOM_GIFT_NORMAL_2_ITEM      equ ITEM_SUPER_POTION  // vanilla
MOM_GIFT_NORMAL_2_THRESHOLD equ 7000               // vanilla
MOM_GIFT_NORMAL_2_COST      equ 600                // vanilla

// Entry 3
MOM_GIFT_NORMAL_3_ITEM      equ ITEM_SILK_SCARF    // vanilla
MOM_GIFT_NORMAL_3_THRESHOLD equ 10000              // vanilla
MOM_GIFT_NORMAL_3_COST      equ 100                // vanilla

// Entry 4
MOM_GIFT_NORMAL_4_ITEM      equ ITEM_MOON_STONE    // vanilla
MOM_GIFT_NORMAL_4_THRESHOLD equ 15000              // vanilla
MOM_GIFT_NORMAL_4_COST      equ 3000               // vanilla

// Entry 5
MOM_GIFT_NORMAL_5_ITEM      equ ITEM_HYPER_POTION  // vanilla
MOM_GIFT_NORMAL_5_THRESHOLD equ 19000              // vanilla
MOM_GIFT_NORMAL_5_COST      equ 900                // vanilla

// Entry 6
MOM_GIFT_NORMAL_6_ITEM      equ ITEM_CHOICE_SCARF  // vanilla
MOM_GIFT_NORMAL_6_THRESHOLD equ 30000              // vanilla
MOM_GIFT_NORMAL_6_COST      equ 200                // vanilla

// Entry 7
MOM_GIFT_NORMAL_7_ITEM      equ ITEM_MUSCLE_BAND   // vanilla
MOM_GIFT_NORMAL_7_THRESHOLD equ 40000              // vanilla
MOM_GIFT_NORMAL_7_COST      equ 200                // vanilla

// Entry 8
MOM_GIFT_NORMAL_8_ITEM      equ ITEM_FOCUS_SASH    // vanilla
MOM_GIFT_NORMAL_8_THRESHOLD equ 50000              // vanilla
MOM_GIFT_NORMAL_8_COST      equ 200                // vanilla

// ============================================================
// CONFIGURATION — berry gift table (17 entries, random pick)
// ============================================================
// How many savings tiers must be crossed for a berry gift to fire.
// Vanilla: one berry gift per 3000 saved (e.g. at 3000, 6000, 9000...).
MOM_GIFT_BERRY_THRESHOLD equ 3000  // vanilla

// Quantity and cost are shared across all berry entries.
MOM_GIFT_BERRY_QTY  equ 5    // vanilla
MOM_GIFT_BERRY_COST equ 100  // vanilla

// The 17 berries to pick from (all typed resist berries in vanilla).
// Replace any entry to swap in a different berry.
MOM_GIFT_BERRY_0_ITEM  equ ITEM_OCCA_BERRY    // vanilla
MOM_GIFT_BERRY_1_ITEM  equ ITEM_PASSHO_BERRY  // vanilla
MOM_GIFT_BERRY_2_ITEM  equ ITEM_WACAN_BERRY   // vanilla
MOM_GIFT_BERRY_3_ITEM  equ ITEM_RINDO_BERRY   // vanilla
MOM_GIFT_BERRY_4_ITEM  equ ITEM_YACHE_BERRY   // vanilla
MOM_GIFT_BERRY_5_ITEM  equ ITEM_CHOPLE_BERRY  // vanilla
MOM_GIFT_BERRY_6_ITEM  equ ITEM_KEBIA_BERRY   // vanilla
MOM_GIFT_BERRY_7_ITEM  equ ITEM_SHUCA_BERRY   // vanilla
MOM_GIFT_BERRY_8_ITEM  equ ITEM_COBA_BERRY    // vanilla
MOM_GIFT_BERRY_9_ITEM  equ ITEM_PAYAPA_BERRY  // vanilla
MOM_GIFT_BERRY_10_ITEM equ ITEM_TANGA_BERRY   // vanilla
MOM_GIFT_BERRY_11_ITEM equ ITEM_CHARTI_BERRY  // vanilla
MOM_GIFT_BERRY_12_ITEM equ ITEM_KASIB_BERRY   // vanilla
MOM_GIFT_BERRY_13_ITEM equ ITEM_HABAN_BERRY   // vanilla
MOM_GIFT_BERRY_14_ITEM equ ITEM_COLBUR_BERRY  // vanilla
MOM_GIFT_BERRY_15_ITEM equ ITEM_BABIRI_BERRY  // vanilla
MOM_GIFT_BERRY_16_ITEM equ ITEM_CHILAN_BERRY  // vanilla

// ============================================================
// PATCH — do not edit below this line
// ============================================================

.nds
.thumb

.open "base/arm9.bin", 0x02000000

.if MOM_GIFT_CONFIG == 1

// sGiftBerryTable[17]: { u8 berryOffset, u8 quantity, u8 cost }
// berryOffset = itemId - ITEM_CHERI_BERRY (149)
// Verified at 0x02108340 in vanilla arm9.bin.
.org 0x02108340
.byte (MOM_GIFT_BERRY_0_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_1_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_2_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_3_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_4_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_5_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_6_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_7_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_8_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_9_ITEM  - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_10_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_11_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_12_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_13_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_14_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_15_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST
.byte (MOM_GIFT_BERRY_16_ITEM - ITEM_CHERI_BERRY), MOM_GIFT_BERRY_QTY, MOM_GIFT_BERRY_COST

// sGiftNormalTable[9]: { u16 itemId, u16 threshold, u16 cost }
// Verified at 0x02108374 in vanilla arm9.bin.
.org 0x02108374
.hword MOM_GIFT_NORMAL_0_ITEM, MOM_GIFT_NORMAL_0_THRESHOLD, MOM_GIFT_NORMAL_0_COST
.hword MOM_GIFT_NORMAL_1_ITEM, MOM_GIFT_NORMAL_1_THRESHOLD, MOM_GIFT_NORMAL_1_COST
.hword MOM_GIFT_NORMAL_2_ITEM, MOM_GIFT_NORMAL_2_THRESHOLD, MOM_GIFT_NORMAL_2_COST
.hword MOM_GIFT_NORMAL_3_ITEM, MOM_GIFT_NORMAL_3_THRESHOLD, MOM_GIFT_NORMAL_3_COST
.hword MOM_GIFT_NORMAL_4_ITEM, MOM_GIFT_NORMAL_4_THRESHOLD, MOM_GIFT_NORMAL_4_COST
.hword MOM_GIFT_NORMAL_5_ITEM, MOM_GIFT_NORMAL_5_THRESHOLD, MOM_GIFT_NORMAL_5_COST
.hword MOM_GIFT_NORMAL_6_ITEM, MOM_GIFT_NORMAL_6_THRESHOLD, MOM_GIFT_NORMAL_6_COST
.hword MOM_GIFT_NORMAL_7_ITEM, MOM_GIFT_NORMAL_7_THRESHOLD, MOM_GIFT_NORMAL_7_COST
.hword MOM_GIFT_NORMAL_8_ITEM, MOM_GIFT_NORMAL_8_THRESHOLD, MOM_GIFT_NORMAL_8_COST

// BERRY_THRESHOLD literal pool in MomGift_TryEnqueueGiftOnBalanceChange.
// Verified at 0x0209329C in vanilla arm9.bin (LE32 = 3000 = 0x0BB8).
// Preceded by C0 46 (NOP padding), followed by function data.
.org 0x0209329C
.word MOM_GIFT_BERRY_THRESHOLD

.endif

.close
