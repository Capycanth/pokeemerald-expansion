// Battle test arena data. Included by src/test_arena.c.
//
// To add a battle, add a line to sTestArenaEntries:
//   ARENA_FIGHT("Label", TRAINER_ID, playerLevel)
// To add a back-to-back run (HP carries over between fights), write a
// TRAINER_NONE-terminated list of trainers and use ARENA_GAUNTLET.
// The player's team is always the starter picked on the first screen,
// created at playerLevel with TEST_ARENA_IVS in every stat and no EVs.

// Starters offered on the first screen.
static const u16 sTestArenaStarters[] =
{
    SPECIES_SPHEAL,
    SPECIES_ROLYCOLY,
    SPECIES_SEEDOT,
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
    // The ladder as played: start at Lv 5, one Potion for the whole run.
    ARENA_GAUNTLET("Ladder run (1 Potion)", sTestArenaLadder, 5, 1),

    // Single ladder fights at equal level and full HP.
    ARENA_FIGHT("Ladder 1: Tessa (Lv 3)",  TRAINER_LADDER_TESSA, 3),
    ARENA_FIGHT("Ladder 2: Rowan (Lv 4)",  TRAINER_LADDER_ROWAN, 4),
    ARENA_FIGHT("Ladder 3: Clara (Lv 5)",  TRAINER_LADDER_CLARA, 5),
    ARENA_FIGHT("Ladder 4: Felix (Lv 6)",  TRAINER_LADDER_FELIX, 6),
    ARENA_FIGHT("Ladder 5: Nadia (Lv 7)",  TRAINER_LADDER_NADIA, 7),
    ARENA_FIGHT("Ladder 6: Hugo (Lv 8)",   TRAINER_LADDER_HUGO,  8),
    ARENA_FIGHT("Ladder 7: Ivy (Lv 9)",    TRAINER_LADDER_IVY,   9),
    ARENA_FIGHT("Ladder 8: Silas (Lv 10)", TRAINER_LADDER_SILAS, 10),

    // Open Tournament, starter at the level cap.
    ARENA_FIGHT("Tournament 1: Barrett",  TRAINER_GRAD_BARRETT,  15),
    ARENA_FIGHT("Tournament 2: Tobias",   TRAINER_GRAD_TOBIAS,   15),
    ARENA_FIGHT("Tournament 3: Juniper",  TRAINER_GRAD_JUNIPER,  15),
    ARENA_FIGHT("Tournament 4: Percival", TRAINER_GRAD_PERCIVAL, 15),
};

#undef ARENA_FIGHT
#undef ARENA_GAUNTLET
