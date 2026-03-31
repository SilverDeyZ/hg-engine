#include "../../include/config.h"

#ifdef IMPLEMENT_WILD_LEVEL_SCALING

#include "../../include/types.h"
#include "../../include/battle.h"
#include "../../include/pokemon.h"
#include "../../include/wild_level_scaling.h"

u8 ApplyWildLevelScaling(u8 vanillaLevel, struct BATTLE_PARAM *battleParam)
{
    s32 newLevel;
    u8 leadLevel = 0;
    struct PartyPokemon *lead = Party_GetMonByIndex(battleParam->poke_party[BATTLER_PLAYER], 0);

    if (lead != NULL)
        leadLevel = (u8)GetMonData(lead, MON_DATA_LEVEL, NULL);

    if (leadLevel <= vanillaLevel)
        return vanillaLevel;

    newLevel = ((s32)vanillaLevel + (s32)leadLevel + 1) / 2;

    if (newLevel < 1)   newLevel = 1;
    if (newLevel > 100) newLevel = 100;

    return (u8)newLevel;
}

#endif
