.nds
.thumb

// Configurable following-Pokemon accessory gift redirect.
// When enabled, state 3 of Task_FollowMonInteract delegates to
// FollowMonGift_HandleAccessoryState in main code, which can swap
// selected accessory rewards into bag items.

.if FOLLOW_MON_GIFT_ITEM_REDIRECT == 1

.open "base/overlay/overlay_0002.bin", 0x02245B80

.org 0x02250314
    mov r0, r4
    mov r1, r6
    bl FollowMonGift_HandleAccessoryState
    b 0x0225047E

.close

.endif
