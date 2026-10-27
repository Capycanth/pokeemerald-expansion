#ifndef GUARD_TEST_ARENA_H
#define GUARD_TEST_ARENA_H

#include "config/test_arena.h"

#if RELEASE
    #define TEST_ARENA FALSE
#else
    #define TEST_ARENA ENABLE_TEST_ARENA
#endif

// TRUE while a battle started from the test arena is running.
extern EWRAM_DATA bool8 gIsTestArenaBattle;

// Replaces the copyright screen and intro: call once the save and heap are set up at boot.
void TestArena_StartFromBoot(void);

#endif // GUARD_TEST_ARENA_H
