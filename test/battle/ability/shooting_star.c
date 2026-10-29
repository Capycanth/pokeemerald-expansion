#include "global.h"
#include "test/battle.h"

ASSUMPTIONS
{
    ASSUME(GetMoveEffect(MOVE_METEOR_BEAM) == EFFECT_TWO_TURNS_ATTACK);
    ASSUME(GetMoveEffect(MOVE_SPORE) == EFFECT_NON_VOLATILE_STATUS);
}

SINGLE_BATTLE_TEST("Shooting Star lets Core Form Minior use a two-turn move on the first turn")
{
    GIVEN {
        PLAYER(SPECIES_MINIOR_CORE) { Ability(ABILITY_SHOOTING_STAR); HP(40); MaxHP(100); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_METEOR_BEAM); }
    } SCENE {
        ABILITY_POPUP(player, ABILITY_SHOOTING_STAR);
        HP_BAR(opponent);
    } THEN {
        EXPECT_EQ(player->species, SPECIES_MINIOR_CORE);
        EXPECT_EQ(player->statStages[STAT_SPATK], DEFAULT_STAT_STAGE + 1);
    }
}

SINGLE_BATTLE_TEST("Shooting Star does not skip the charging turn in Meteor Form")
{
    GIVEN {
        PLAYER(SPECIES_MINIOR_METEOR) { Ability(ABILITY_SHOOTING_STAR); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_METEOR_BEAM); }
    } SCENE {
        NONE_OF {
            ABILITY_POPUP(player, ABILITY_SHOOTING_STAR);
            HP_BAR(opponent);
        }
    } THEN {
        EXPECT_EQ(player->species, SPECIES_MINIOR_METEOR);
        EXPECT_EQ(player->statStages[STAT_SPATK], DEFAULT_STAT_STAGE + 1);
    }
}

SINGLE_BATTLE_TEST("Shooting Star does not protect Meteor Form from status conditions")
{
    GIVEN {
        PLAYER(SPECIES_MINIOR_METEOR) { Ability(ABILITY_SHOOTING_STAR); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(opponent, MOVE_SPORE); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_SPORE, opponent);
    } THEN {
        EXPECT(player->status1 & STATUS1_SLEEP);
    }
}

SINGLE_BATTLE_TEST("Shooting Star changes Minior into Core Form at half HP or less")
{
    GIVEN {
        PLAYER(SPECIES_MINIOR_METEOR) { Ability(ABILITY_SHOOTING_STAR); HP(51); MaxHP(100); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(opponent, MOVE_SCRATCH); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_SCRATCH, opponent);
        ABILITY_POPUP(player, ABILITY_SHOOTING_STAR);
        ANIMATION(ANIM_TYPE_GENERAL, B_ANIM_FORM_CHANGE, player);
    } THEN {
        EXPECT_EQ(player->species, SPECIES_MINIOR_CORE);
    }
}
