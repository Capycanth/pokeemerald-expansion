#include "global.h"
#include "test/battle.h"

ASSUMPTIONS
{
    ASSUME(GetMoveAccuracy(MOVE_THUNDER) == 70);
    ASSUME(GetMoveAccuracy(MOVE_THUNDERBOLT) == 100);
    ASSUME(GetMoveAccuracy(MOVE_THREAD_CANNON) == 80);
    ASSUME(GetMoveAccuracy(MOVE_SWIFT) == 0);
    ASSUME(GetMoveCategory(MOVE_THUNDER_WAVE) == DAMAGE_CATEGORY_STATUS);
}

SINGLE_BATTLE_TEST("Spider Sense raises accuracy by 20%")
{
    PASSES_RANDOMLY(84, 100, RNG_ACCURACY);
    GIVEN {
        PLAYER(SPECIES_GALVANTULA) { Ability(ABILITY_SPIDER_SENSE); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_THUNDER); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_THUNDER, player);
        HP_BAR(opponent);
    }
}

SINGLE_BATTLE_TEST("Spider Sense makes Thread Cannon 96% accurate")
{
    PASSES_RANDOMLY(96, 100, RNG_ACCURACY);
    GIVEN {
        PLAYER(SPECIES_GALVANTULA) { Ability(ABILITY_SPIDER_SENSE); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_THREAD_CANNON); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_THREAD_CANNON, player);
        HP_BAR(opponent);
    }
}

SINGLE_BATTLE_TEST("Spider Sense gives +1 priority to attacks that are less than 100% accurate")
{
    enum Ability ability;

    PARAMETRIZE { ability = ABILITY_COMPOUND_EYES; }
    PARAMETRIZE { ability = ABILITY_SPIDER_SENSE; }

    GIVEN {
        PLAYER(SPECIES_GALVANTULA) { Ability(ability); Speed(1); }
        OPPONENT(SPECIES_WOBBUFFET) { Speed(100); }
    } WHEN {
        TURN { MOVE(player, MOVE_THREAD_CANNON); MOVE(opponent, MOVE_CELEBRATE); }
    } SCENE {
        if (ability == ABILITY_SPIDER_SENSE)
        {
            ANIMATION(ANIM_TYPE_MOVE, MOVE_THREAD_CANNON, player);
            ANIMATION(ANIM_TYPE_MOVE, MOVE_CELEBRATE, opponent);
        }
        else
        {
            ANIMATION(ANIM_TYPE_MOVE, MOVE_CELEBRATE, opponent);
            ANIMATION(ANIM_TYPE_MOVE, MOVE_THREAD_CANNON, player);
        }
    }
}

SINGLE_BATTLE_TEST("Spider Sense doesn't give priority to accurate, never-miss, or status moves")
{
    enum Move move;

    PARAMETRIZE { move = MOVE_THUNDERBOLT; }
    PARAMETRIZE { move = MOVE_SWIFT; }
    PARAMETRIZE { move = MOVE_THUNDER_WAVE; }

    GIVEN {
        PLAYER(SPECIES_GALVANTULA) { Ability(ABILITY_SPIDER_SENSE); Speed(1); }
        OPPONENT(SPECIES_WOBBUFFET) { Speed(100); }
    } WHEN {
        TURN { MOVE(player, move); MOVE(opponent, MOVE_CELEBRATE); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_CELEBRATE, opponent);
        ANIMATION(ANIM_TYPE_MOVE, move, player);
    }
}
