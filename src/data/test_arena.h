// Battle test arena data. Included by src/test_arena.c.
//
// To add a battle, add a line to sTestArenaEntries:
//   ARENA_FIGHT("Label", TRAINER_ID, playerLevel)
// Use ARENA_TRAINED as the level to fight with your trained starter: it starts
// at TEST_ARENA_STARTER_LEVEL when picked, is healed before each fight, and
// keeps the EXP, levels and moves it gains. Any other level builds a fresh
// starter at that level for the fight.
// To add a back-to-back run (HP carries over between fights), write a
// TRAINER_NONE-terminated list of trainers and use ARENA_GAUNTLET.
// Starters always have TEST_ARENA_IVS in every stat and no EVs.

// Starters offered on the first screen, with the four moves they know at
// TEST_ARENA_STARTER_LEVEL (Lv 5). At any other level a fresh starter gets
// its normal level-up moves instead.
static const struct TestArenaStarter sTestArenaStarters[] =
{
    {
        .species = SPECIES_SPHEAL,
        .moves = { MOVE_POWDER_SNOW, MOVE_DEFENSE_CURL, MOVE_ROLLOUT, MOVE_ICY_WIND },
    },
    {
        .species = SPECIES_ROLYCOLY,
        .moves = { MOVE_TACKLE, MOVE_SMOKESCREEN, MOVE_ROCK_THROW, MOVE_EMBER },
    },
    {
        .species = SPECIES_SEEDOT,
        .moves = { MOVE_TACKLE, MOVE_HARDEN, MOVE_LEAFAGE, MOVE_BULLET_SEED },
    },
};

// Underground Ladder, all eight in order with no healing between fights.
static const u16 sTestArenaLadder[] =
{
    TRAINER_LADDER_TESSA,
    TRAINER_LADDER_ROWAN,
    TRAINER_LADDER_CLARA,
    TRAINER_LADDER_FELIX,
    TRAINER_LADDER_NADIA,
    TRAINER_LADDER_HUGO,
    TRAINER_LADDER_IVY,
    TRAINER_LADDER_SILAS,
    TRAINER_NONE,
};

#define ARENA_FIGHT(_name, _trainer, _level)                    \
{                                                               \
    .name = COMPOUND_STRING(_name),                             \
    .opponents = (const u16[]) { _trainer, TRAINER_NONE },      \
    .playerLevel = _level,                                      \
    .potions = 0,                                               \
}

#define ARENA_GAUNTLET(_name, _trainers, _level, _potions)      \
{                                                               \
    .name = COMPOUND_STRING(_name),                             \
    .opponents = _trainers,                                     \
    .playerLevel = _level,                                      \
    .potions = _potions,                                        \
}

static const struct TestArenaEntry sTestArenaEntries[] =
{
    // The ladder as played: a fresh Lv 5 starter, one Potion for the whole run.
    ARENA_GAUNTLET("Ladder run (1 Potion)", sTestArenaLadder, TEST_ARENA_STARTER_LEVEL, 1),

    // Single ladder fights with your trained starter: full HP each fight,
    // EXP and levels carry over. The level in the label is the opponent's.
    ARENA_FIGHT("Ladder 1: Tessa (foe Lv 3)",  TRAINER_LADDER_TESSA, ARENA_TRAINED),
    ARENA_FIGHT("Ladder 2: Rowan (foe Lv 4)",  TRAINER_LADDER_ROWAN, ARENA_TRAINED),
    ARENA_FIGHT("Ladder 3: Clara (foe Lv 5)",  TRAINER_LADDER_CLARA, ARENA_TRAINED),
    ARENA_FIGHT("Ladder 4: Felix (foe Lv 6)",  TRAINER_LADDER_FELIX, ARENA_TRAINED),
    ARENA_FIGHT("Ladder 5: Nadia (foe Lv 7)",  TRAINER_LADDER_NADIA, ARENA_TRAINED),
    ARENA_FIGHT("Ladder 6: Hugo (foe Lv 8)",   TRAINER_LADDER_HUGO,  ARENA_TRAINED),
    ARENA_FIGHT("Ladder 7: Ivy (foe Lv 9)",    TRAINER_LADDER_IVY,   ARENA_TRAINED),
    ARENA_FIGHT("Ladder 8: Silas (foe Lv 10)", TRAINER_LADDER_SILAS, ARENA_TRAINED),

    // Open Tournament, a fresh starter at the level cap.
    ARENA_FIGHT("Tournament 1: Barrett",  TRAINER_GRAD_BARRETT,  15),
    ARENA_FIGHT("Tournament 2: Tobias",   TRAINER_GRAD_TOBIAS,   15),
    ARENA_FIGHT("Tournament 3: Juniper",  TRAINER_GRAD_JUNIPER,  15),
    ARENA_FIGHT("Tournament 4: Percival", TRAINER_GRAD_PERCIVAL, 15),
};

#undef ARENA_FIGHT
#undef ARENA_GAUNTLET
