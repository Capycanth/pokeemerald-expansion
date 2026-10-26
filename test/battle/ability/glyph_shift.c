#include "global.h"
#include "test/battle.h"

SINGLE_BATTLE_TEST("Glyph Shift changes the user's type to the move's type every time, even with Gen 9 Protean rules")
{
    GIVEN {
        WITH_CONFIG(B_PROTEAN_LIBERO, GEN_9);
        PLAYER(SPECIES_UNOWN) { Ability(ABILITY_GLYPH_SHIFT); }
        OPPONENT(SPECIES_REGIROCK);
    } WHEN {
        TURN { MOVE(player, MOVE_WATER_GUN); }
        TURN { MOVE(player, MOVE_SCRATCH); }
        TURN { MOVE(player, MOVE_WATER_GUN); }
    } SCENE {
        ABILITY_POPUP(player, ABILITY_GLYPH_SHIFT);
        MESSAGE("Unown transformed into the Water type!");
        ANIMATION(ANIM_TYPE_MOVE, MOVE_WATER_GUN, player);
        ABILITY_POPUP(player, ABILITY_GLYPH_SHIFT);
        MESSAGE("Unown transformed into the Normal type!");
        ANIMATION(ANIM_TYPE_MOVE, MOVE_SCRATCH, player);
        ABILITY_POPUP(player, ABILITY_GLYPH_SHIFT);
        MESSAGE("Unown transformed into the Water type!");
        ANIMATION(ANIM_TYPE_MOVE, MOVE_WATER_GUN, player);
    }
}

SINGLE_BATTLE_TEST("Glyph Shift does not activate if the user is already the move's type")
{
    GIVEN {
        ASSUME(GetMoveType(MOVE_CONFUSION) == TYPE_PSYCHIC);
        PLAYER(SPECIES_UNOWN) { Ability(ABILITY_GLYPH_SHIFT); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_CONFUSION); }
    } SCENE {
        NONE_OF { ABILITY_POPUP(player, ABILITY_GLYPH_SHIFT); }
        ANIMATION(ANIM_TYPE_MOVE, MOVE_CONFUSION, player);
    }
}
