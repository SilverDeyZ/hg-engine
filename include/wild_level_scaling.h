#ifndef WILD_LEVEL_SCALING_H
#define WILD_LEVEL_SCALING_H

#include "config.h"

#ifdef IMPLEMENT_WILD_LEVEL_SCALING

#include "types.h"
#include "battle.h"

u8 ApplyWildLevelScaling(u8 vanillaLevel, struct BATTLE_PARAM *battleParam);

#endif // IMPLEMENT_WILD_LEVEL_SCALING

#endif // WILD_LEVEL_SCALING_H
