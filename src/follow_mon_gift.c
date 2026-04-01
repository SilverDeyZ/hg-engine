#include "../include/bag.h"
#include "../include/constants/item.h"
#include "../include/constants/sndseq.h"
#include "../include/pokemon.h"
#include "../include/save.h"
#include "../include/types.h"

typedef struct FashionCase {
    u32 unk_00[40 / sizeof(u32)];
    u32 unk_28[18 / sizeof(u32)];
    u8 padding_3C[4];
} FashionCase;

typedef struct SaveFashionDataSub {
    u8 filler_00[0x74];
} SaveFashionDataSub;

typedef struct SaveFashionDataSub3FC {
    u8 filler_00[0x98];
} SaveFashionDataSub3FC;

typedef struct SaveFashionData {
    SaveFashionDataSub unk_000[11];
    SaveFashionDataSub3FC unk_3FC[5];
    FashionCase fashionCase;
} SaveFashionData;

typedef struct FollowMonGiftWork {
    u8 filler_0000[0x816];
    u8 accessoryGiftIdPlusOne;
} FollowMonGiftWork;

#define FOLLOW_MON_GIFT_WORK_OFFSET 0x120
#define SAVE_BAG_ARRAY_ID 3
#define HEAP_ID_FIELD1_VALUE 4

extern void *SaveArray_Get(SaveData *saveData, int id);
static void FollowMonGift_ShowMessage(FieldSystem *fieldSystem, FollowMonGiftWork *work, int messageId) {
    ((void (*)(FieldSystem *, FollowMonGiftWork *, int))0x0224FC09)(fieldSystem, work, messageId);
}

static void FollowMonGift_PlayAccessoryFanfare(void) {
    ((void (*)(u16))0x02006B25)(SEQ_ME_ACCE);
}

static SaveFashionData *FollowMonGift_GetFashionData(SaveData *saveData) {
    return ((SaveFashionData *(*)(SaveData *))0x0202C029)(saveData);
}

static FashionCase *FollowMonGift_GetFashionCase(SaveFashionData *fashionData) {
    return ((FashionCase *(*)(SaveFashionData *))0x0202B9E1)(fashionData);
}

static int FollowMonGift_FashionCaseHasSpace(FashionCase *fashionCase, int accessoryId, int quantity) {
    return ((int (*)(FashionCase *, int, int))0x0202BA2D)(fashionCase, accessoryId, quantity);
}

static void FollowMonGift_GiveFashionItem(FashionCase *fashionCase, int accessoryId, int quantity) {
    ((void (*)(FashionCase *, int, int))0x0202BB09)(fashionCase, accessoryId, quantity);
}

static const u16 sFollowMonAccessoryItemRedirect[100] = {
    [0] = ITEM_NONE,  // White Fluff - Route 31
    [1] = ITEM_NONE,  // Yellow Fluff - Route 2
    [2] = ITEM_NONE,  // Pink Fluff - Routes 16, 33
    [3] = ITEM_NONE,  // Brown Fluff - Route 39
    [4] = ITEM_NONE,  // Black Fluff - Route 42, Dark Cave
    [5] = ITEM_NONE,  // Orange Fluff - Routes 15, 36
    [6] = ITEM_NONE,  // Round Pebble - Route 10, Mt. Moon
    [7] = ITEM_NONE,  // Glitter Boulder - Route 24
    [8] = ITEM_NONE,  // Snaggy Pebble - Mt. Silver Outside, Diglett's Cave
    [9] = ITEM_NONE,  // Jagged Boulder - Mt. Silver Outside, Diglett's Cave, Rock Mountain
    [10] = ITEM_NONE, // Black Pebble - Union Cave, Dark Cave, Rock Tunnel, Cerulean Cave
    [11] = ITEM_NONE, // Mini Pebble - Routes 10, 26
    [12] = ITEM_NONE, // Pink Scale - Routes 13, 40, Cerulean City
    [13] = ITEM_NONE, // Blue Scale - Routes 14, 20, 41, Mahogany Town, Lake of Rage
    [14] = ITEM_NONE, // Green Scale - Route 34
    [15] = ITEM_NONE, // Purple Scale - Route 47, Lake of Rage
    [16] = ITEM_NONE, // Big Scale - Routes 27, 48, Olivine City
    [17] = ITEM_NONE, // Narrow Scale - Routes 2, 12, Lake of Rage
    [18] = ITEM_NONE, // Blue Feather - Route 37
    [19] = ITEM_NONE, // Red Feather - Route 38
    [20] = ITEM_NONE, // Yellow Feather - Route 3
    [21] = ITEM_NONE, // White Feather - Route 4
    [22] = ITEM_NONE, // Black Moustache - Sprout Tower, Bell Tower, Dragon's Den
    [23] = ITEM_NONE, // White Moustache - Bell Tower, Dragon's Den
    [24] = ITEM_NONE, // Black Beard - Sprout Tower
    [25] = ITEM_NONE, // White Beard - Sprout Tower
    [26] = ITEM_NONE, // Small Leaf - Routes 5, 8
    [27] = ITEM_NONE, // Big Leaf - Route 6
    [28] = ITEM_NONE, // Narrow Leaf - Route 7
    [29] = ITEM_NONE, // Shed Claw - Whirl Islands, Mt. Silver
    [30] = ITEM_NONE, // Shed Horn - Whirl Islands, Mt. Silver
    [31] = ITEM_NONE, // Thin Mushroom - Ilex Forest
    [32] = ITEM_NONE, // Thick Mushroom - Ilex Forest, Viridian Forest
    [33] = ITEM_NONE, // Stump - Ilex Forest, Viridian Forest
    [34] = ITEM_NONE, // Pretty Dewdrop - Dragon's Den, Mt. Silver, Viridian Forest
    [35] = ITEM_NONE, // Snow Crystal - Ice Path, Mt. Silver
    [36] = ITEM_NONE, // Sparks - Shining Lighthouse
    [37] = ITEM_NONE, // Shimmering Fire - Burnt Tower, Shining Lighthouse
    [38] = ITEM_NONE, // Mystic Fire - Burnt Tower, Shining Lighthouse
    [39] = ITEM_NONE, // Determination - Ruins of Alph, Mahogany Town Rocket Hideout
    [40] = ITEM_NONE, // Peculiar Spoon - Goldenrod City Radio Tower
    [41] = ITEM_NONE, // Puffy Smoke - Burnt Tower, Bell Tower
    [42] = ITEM_NONE, // Poison Extract - Ruins of Alph, Mahogany Town Rocket Hideout, Cerulean Cave
    [43] = ITEM_NONE, // Wealthy Coin - SS Aqua
    [44] = ITEM_NONE, // Eerie Thing - Ruins of Alph, Victory Road
    [45] = ITEM_NONE, // Spring - Goldenrod City Radio Tower
    [46] = ITEM_NONE, // Seashell - Whirl Islands
    [48] = ITEM_NONE, // Shiny Powder - Radio Tower, Mt. Moon
    [49] = ITEM_NONE, // Glitter Powder - Power Plant
    [50] = ITEM_NONE, // Red Flower - Route 35, Ecruteak City
    [51] = ITEM_NONE, // Pink Flower - Route 30
    [52] = ITEM_NONE, // White Flower - Routes 9, 32
    [53] = ITEM_NONE, // Blue Flower - Route 11
    [54] = ITEM_NONE, // Orange Flower - Route 43, Ecruteak City
    [55] = ITEM_NONE, // Yellow Flower - Route 1, Ecruteak City, Viridian City, Pewter City, Cerulean City, Vermillion City, Celadon City, Lavender Town, Fuchsia City
};

void FollowMonGift_HandleAccessoryState(FieldSystem *fieldSystem, int *statePtr) {
    SaveData *saveData;
    FollowMonGiftWork *work;
    u8 giftIdPlusOne;
    int accessoryId;
    u16 itemId;

    if (fieldSystem == NULL || statePtr == NULL) {
        return;
    }

    saveData = fieldSystem->savedata;
    work = *(FollowMonGiftWork **)((u8 *)fieldSystem + FOLLOW_MON_GIFT_WORK_OFFSET);
    if (saveData == NULL || work == NULL) {
        *statePtr = 5;
        return;
    }

    giftIdPlusOne = work->accessoryGiftIdPlusOne;
    if (giftIdPlusOne == 0) {
        *statePtr = 5;
        return;
    }

    accessoryId = giftIdPlusOne - 1;
    if ((unsigned)accessoryId >= 100) {
        *statePtr = 5;
        return;
    }

    itemId = sFollowMonAccessoryItemRedirect[accessoryId];
    if (itemId != ITEM_NONE) {
        BAG_DATA *bag = SaveArray_Get(saveData, SAVE_BAG_ARRAY_ID);
        if (Bag_HasSpaceForItem(bag, itemId, 1, HEAP_ID_FIELD1_VALUE)) {
            Bag_AddItem(bag, itemId, 1, HEAP_ID_FIELD1_VALUE);
            FollowMonGift_ShowMessage(fieldSystem, work, 3);
            FollowMonGift_PlayAccessoryFanfare();
        } else {
            FollowMonGift_ShowMessage(fieldSystem, work, 2);
        }
        *statePtr = 5;
        return;
    }

    {
        FashionCase *fashionCase = FollowMonGift_GetFashionCase(FollowMonGift_GetFashionData(saveData));
        if (FollowMonGift_FashionCaseHasSpace(fashionCase, accessoryId, 1)) {
            FollowMonGift_GiveFashionItem(fashionCase, accessoryId, 1);
            FollowMonGift_ShowMessage(fieldSystem, work, 3);
            FollowMonGift_PlayAccessoryFanfare();
        } else {
            FollowMonGift_ShowMessage(fieldSystem, work, 2);
        }
    }

    *statePtr = 5;
}
