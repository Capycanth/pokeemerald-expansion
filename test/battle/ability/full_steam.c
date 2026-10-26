#include "global.h"
#include "test/battle.h"

ASSUMPTIONS
{
    ASSUME(GetMoveType(MOVE_EMBER) == TYPE_FIRE);
    ASSUME(GetMoveType(MOVE_WATER_GUN) == TYPE_WATER);
    ASSUME(GetMoveEffect(MOVE_WORRY_SEED) == EFFECT_OVERWRITE_ABILITY);
}

SINGLE_BATTLE_TEST("Full Steam raises Speed by 6 stages when hit by a Fire or Water move")
{
    enum Move move;

    PARAMETRIZE { move = MOVE_EMBER; }
    PARAMETRIZE { move = MOVE_WATER_GUN; }

    GIVEN {
        PLAYER(SPECIES_COALOSSAL) { Ability(ABILITY_FULL_STEAM); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(opponent, move); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, move, opponent);
        ABILITY_POPUP(player, ABILITY_FULL_STEAM);
        MESSAGE("Coalossal's Speed rose drastically!");
    } THEN {
        EXPECT_EQ(player->statStages[STAT_SPEED], DEFAULT_STAT_STAGE + 6);
    }
}

SINGLE_BATTLE_TEST("Full Steam halves damage from Fire and Water moves", s16 damage[2])
{
    enum Move move;

    PARAMETRIZE { move = MOVE_EMBER; }
    PARAMETRIZE { move = MOVE_WATER_GUN; }

    GIVEN {
        PLAYER(SPECIES_WOBBUFFET);
        OPPONENT(SPECIES_COALOSSAL) { Ability(ABILITY_FULL_STEAM); }
    } WHEN {
        TURN { MOVE(player, move); }
        TURN { MOVE(player, MOVE_WORRY_SEED); }
        TURN { MOVE(player, move); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, move, player);
        HP_BAR(opponent, captureDamage: &results[i].damage[0]);
        ANIMATION(ANIM_TYPE_MOVE, MOVE_WORRY_SEED, player);
        ANIMATION(ANIM_TYPE_MOVE, move, player);
        HP_BAR(opponent, captureDamage: &results[i].damage[1]);
    } FINALLY {
        EXPECT_MUL_EQ(results[0].damage[0], Q_4_12(2), results[0].damage[1]);
        EXPECT_MUL_EQ(results[1].damage[0], Q_4_12(2), results[1].damage[1]);
    }
}
