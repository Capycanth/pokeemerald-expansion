#include "global.h"
#include "test/battle.h"

ASSUMPTIONS
{
    ASSUME(GetMoveEffect(MOVE_REFLECT) == EFFECT_REFLECT);
    ASSUME(GetMoveEffect(MOVE_LIGHT_SCREEN) == EFFECT_LIGHT_SCREEN);
}

SINGLE_BATTLE_TEST("Starlight makes Reflect and Light Screen last 8 turns", u8 reflectTimer, u8 lightScreenTimer)
{
    enum Ability ability;

    PARAMETRIZE { ability = ABILITY_TRIAGE; }
    PARAMETRIZE { ability = ABILITY_STARLIGHT; }

    GIVEN {
        PLAYER(SPECIES_LEDIAN) { Ability(ability); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_REFLECT); }
        TURN { MOVE(player, MOVE_LIGHT_SCREEN); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_REFLECT, player);
        ANIMATION(ANIM_TYPE_MOVE, MOVE_LIGHT_SCREEN, player);
    } THEN {
        results[i].reflectTimer = gSideTimers[B_SIDE_PLAYER].reflectTimer;
        results[i].lightScreenTimer = gSideTimers[B_SIDE_PLAYER].lightscreenTimer;
    } FINALLY {
        EXPECT_EQ(results[1].reflectTimer, results[0].reflectTimer + 3);
        EXPECT_EQ(results[1].lightScreenTimer, results[0].lightScreenTimer + 3);
    }
}

SINGLE_BATTLE_TEST("Starlight Reflect is still up after 7 turns")
{
    GIVEN {
        PLAYER(SPECIES_LEDIAN) { Ability(ABILITY_STARLIGHT); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_REFLECT); }
        TURN {}
        TURN {}
        TURN {}
        TURN {}
        TURN {}
        TURN {}
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_REFLECT, player);
        NONE_OF { MESSAGE("Your side's Reflect wore off!"); }
    }
}

SINGLE_BATTLE_TEST("Starlight Reflect wears off at the end of the 8th turn")
{
    GIVEN {
        PLAYER(SPECIES_LEDIAN) { Ability(ABILITY_STARLIGHT); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_REFLECT); }
        TURN {}
        TURN {}
        TURN {}
        TURN {}
        TURN {}
        TURN {}
        TURN {}
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_REFLECT, player);
        MESSAGE("Your side's Reflect wore off!");
    }
}
