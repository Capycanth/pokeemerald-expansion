// Battle test arena.
//
// When ENABLE_TEST_ARENA is TRUE (include/config/test_arena.h), the game boots
// straight into this menu instead of the intro. The first screen picks a
// starter; the second lists the battles in src/data/test_arena.h. Each battle
// rebuilds the starter at that battle's level with full HP, then returns here
// with the result. A gauntlet entry runs its trainers back to back with HP
// carried over, stopping between fights so a Potion can be used.
//
// Nothing here is ever saved.

#include "global.h"
#include "test_arena.h"
#include "battle.h"
#include "battle_main.h"
#include "battle_setup.h"
#include "bg.h"
#include "data.h"
#include "gpu_regs.h"
#include "item.h"
#include "main.h"
#include "menu.h"
#include "money.h"
#include "new_game.h"
#include "palette.h"
#include "pokemon.h"
#include "scanline_effect.h"
#include "sound.h"
#include "sprite.h"
#include "string_util.h"
#include "task.h"
#include "text.h"
#include "window.h"
#include "constants/battle.h"
#include "constants/items.h"
#include "constants/rgb.h"
#include "constants/songs.h"
#include "constants/species.h"
#include "constants/trainers.h"

struct TestArenaEntry
{
    const u8 *name;
    const u16 *opponents;   // TRAINER_NONE-terminated. More than one = gauntlet.
    u8 playerLevel;         // Starter's level at the start of the entry.
    u8 potions;             // Potions in the Bag at the start of the entry.
};

#include "data/test_arena.h"

enum TestArenaScreen
{
    ARENA_SCREEN_STARTER,
    ARENA_SCREEN_BATTLES,
    ARENA_SCREEN_GAUNTLET,
    ARENA_SCREEN_COUNT,
};

enum TestArenaResult
{
    ARENA_RESULT_NONE,
    ARENA_RESULT_WON,
    ARENA_RESULT_LOST,
    ARENA_RESULT_GAUNTLET_CLEARED,
    ARENA_RESULT_GAUNTLET_LOST,
    ARENA_RESULT_GAUNTLET_QUIT,
};

enum
{
    GAUNTLET_ROW_FIGHT,
    GAUNTLET_ROW_POTION,
    GAUNTLET_ROW_GIVE_UP,
    GAUNTLET_ROW_COUNT,
};

enum
{
    WIN_TITLE,
    WIN_LIST,
    WIN_FOOTER,
};

#define ROW_HEIGHT      16
#define ROWS_VISIBLE    6
#define LIST_TEXT_X     10
#define TEXT_BUFFER_LEN 64

struct TestArena
{
    u8 screen;
    u8 starter;                         // Index into sTestArenaStarters.
    u8 cursor[ARENA_SCREEN_COUNT];
    u8 scroll[ARENA_SCREEN_COUNT];
    u8 entry;                           // Index into sTestArenaEntries.
    u8 fight;                           // Index into the entry's opponents.
    u8 result;                          // enum TestArenaResult
    u16 resultTrainer;
    u32 moneyBeforeFight;
    u32 lastPrize;
    u32 runPrize;
};

EWRAM_DATA bool8 gIsTestArenaBattle = FALSE;
static EWRAM_DATA struct TestArena sArena = {0};

static void CB2_InitArenaScreen(void);
static void CB2_TestArena(void);
static void CB2_StartArenaBattle(void);
static void CB2_ReturnFromArenaBattle(void);

static const u16 sBackdropColor[] = { RGB(3, 7, 13) };

static const u8 sColorsNormal[]   = { TEXT_COLOR_WHITE, TEXT_COLOR_DARK_GRAY, TEXT_COLOR_LIGHT_GRAY };
static const u8 sColorsSelected[] = { TEXT_COLOR_WHITE, TEXT_COLOR_BLUE,      TEXT_COLOR_LIGHT_BLUE };
static const u8 sColorsHint[]     = { TEXT_COLOR_WHITE, TEXT_COLOR_LIGHT_GRAY, TEXT_COLOR_WHITE };

static const struct BgTemplate sArenaBgTemplates[] =
{
    {
        .bg = 0,
        .charBaseIndex = 0,
        .mapBaseIndex = 31,
        .screenSize = 0,
        .paletteMode = 0,
        .priority = 0,
        .baseTile = 0,
    },
};

static const struct WindowTemplate sArenaWindowTemplates[] =
{
    [WIN_TITLE] =
    {
        .bg = 0,
        .tilemapLeft = 1,
        .tilemapTop = 0,
        .width = 28,
        .height = 2,
        .paletteNum = 15,
        .baseBlock = 1,
    },
    [WIN_LIST] =
    {
        .bg = 0,
        .tilemapLeft = 1,
        .tilemapTop = 3,
        .width = 28,
        .height = ROWS_VISIBLE * ROW_HEIGHT / 8,
        .paletteNum = 15,
        .baseBlock = 1 + 28 * 2,
    },
    [WIN_FOOTER] =
    {
        .bg = 0,
        .tilemapLeft = 1,
        .tilemapTop = 16,
        .width = 28,
        .height = 4,
        .paletteNum = 15,
        .baseBlock = 1 + 28 * 2 + 28 * (ROWS_VISIBLE * ROW_HEIGHT / 8),
    },
    DUMMY_WIN_TEMPLATE
};

// ---------------------------------------------------------------------------
// Helpers

static const struct TestArenaEntry *GetCurrentEntry(void)
{
    return &sTestArenaEntries[sArena.entry];
}

static u32 GetEntryFightCount(const struct TestArenaEntry *entry)
{
    u32 count = 0;
    while (entry->opponents[count] != TRAINER_NONE)
        count++;
    return count;
}

static bool32 IsGauntlet(const struct TestArenaEntry *entry)
{
    return GetEntryFightCount(entry) > 1;
}

static u16 GetCurrentOpponent(void)
{
    return GetCurrentEntry()->opponents[sArena.fight];
}

static u8 *AppendNumber(u8 *end, u32 value)
{
    return ConvertIntToDecimalStringN(end, value, STR_CONV_MODE_LEFT_ALIGN, 6);
}

// "SPHEAL Lv 6  HP 14/22", or "SPHEAL HP 14/22" without the level.
static void BufferLeadMonStatus(u8 *dst, bool32 showLevel)
{
    struct Pokemon *mon = &gPlayerParty[0];
    u8 *end = StringCopy(dst, GetSpeciesName(GetMonData(mon, MON_DATA_SPECIES)));
    if (showLevel)
    {
        end = StringCopy(end, COMPOUND_STRING(" Lv "));
        end = AppendNumber(end, GetMonData(mon, MON_DATA_LEVEL));
        end = StringCopy(end, COMPOUND_STRING(" "));
    }
    end = StringCopy(end, COMPOUND_STRING(" HP "));
    end = AppendNumber(end, GetMonData(mon, MON_DATA_HP));
    end = StringCopy(end, COMPOUND_STRING("/"));
    AppendNumber(end, GetMonData(mon, MON_DATA_MAX_HP));
}

static u32 GetRowCount(void)
{
    switch (sArena.screen)
    {
    case ARENA_SCREEN_STARTER:
        return ARRAY_COUNT(sTestArenaStarters);
    case ARENA_SCREEN_BATTLES:
        return ARRAY_COUNT(sTestArenaEntries);
    case ARENA_SCREEN_GAUNTLET:
    default:
        return GAUNTLET_ROW_COUNT;
    }
}

static void BufferRowText(u32 row, u8 *dst)
{
    u8 *end;

    switch (sArena.screen)
    {
    case ARENA_SCREEN_STARTER:
        StringCopy(dst, GetSpeciesName(sTestArenaStarters[row]));
        break;
    case ARENA_SCREEN_BATTLES:
        StringCopy(dst, sTestArenaEntries[row].name);
        break;
    case ARENA_SCREEN_GAUNTLET:
        switch (row)
        {
        case GAUNTLET_ROW_FIGHT:
            end = StringCopy(dst, COMPOUND_STRING("Fight "));
            StringCopy(end, GetTrainerNameFromId(GetCurrentOpponent()));
            break;
        case GAUNTLET_ROW_POTION:
            end = StringCopy(dst, COMPOUND_STRING("Use Potion ("));
            end = AppendNumber(end, CountTotalItemQuantityInBag(ITEM_POTION));
            StringCopy(end, COMPOUND_STRING(" left)"));
            break;
        case GAUNTLET_ROW_GIVE_UP:
        default:
            StringCopy(dst, COMPOUND_STRING("Give up"));
            break;
        }
        break;
    }
}

static void BufferTitle(u8 *dst)
{
    u8 *end;

    switch (sArena.screen)
    {
    case ARENA_SCREEN_STARTER:
        StringCopy(dst, COMPOUND_STRING("TEST ARENA - Choose a starter"));
        break;
    case ARENA_SCREEN_BATTLES:
        end = StringCopy(dst, COMPOUND_STRING("TEST ARENA - Starter: "));
        StringCopy(end, GetSpeciesName(sTestArenaStarters[sArena.starter]));
        break;
    case ARENA_SCREEN_GAUNTLET:
        end = StringCopy(dst, GetCurrentEntry()->name);
        end = StringCopy(end, COMPOUND_STRING(" - fight "));
        end = AppendNumber(end, sArena.fight + 1);
        end = StringCopy(end, COMPOUND_STRING("/"));
        AppendNumber(end, GetEntryFightCount(GetCurrentEntry()));
        break;
    }
}

// Footer line 1: what just happened, or status.
static void BufferFooterStatus(u8 *dst)
{
    u8 *end;

    switch (sArena.screen)
    {
    case ARENA_SCREEN_STARTER:
        StringCopy(dst, COMPOUND_STRING("Your only Pokémon in every battle."));
        break;
    case ARENA_SCREEN_GAUNTLET:
        BufferLeadMonStatus(dst, TRUE);
        break;
    case ARENA_SCREEN_BATTLES:
        switch (sArena.result)
        {
        case ARENA_RESULT_WON:
            end = StringCopy(dst, COMPOUND_STRING("Beat "));
            end = StringCopy(end, GetTrainerNameFromId(sArena.resultTrainer));
            end = StringCopy(end, COMPOUND_STRING(" +¥"));
            end = AppendNumber(end, sArena.lastPrize);
            end = StringCopy(end, COMPOUND_STRING(". "));
            BufferLeadMonStatus(end, FALSE);
            break;
        case ARENA_RESULT_LOST:
            end = StringCopy(dst, COMPOUND_STRING("Lost to "));
            end = StringCopy(end, GetTrainerNameFromId(sArena.resultTrainer));
            StringCopy(end, COMPOUND_STRING("."));
            break;
        case ARENA_RESULT_GAUNTLET_CLEARED:
            end = StringCopy(dst, COMPOUND_STRING("Run cleared! Earned ¥"));
            end = AppendNumber(end, sArena.runPrize);
            StringCopy(end, COMPOUND_STRING("."));
            break;
        case ARENA_RESULT_GAUNTLET_LOST:
        case ARENA_RESULT_GAUNTLET_QUIT:
            end = StringCopy(dst, sArena.result == ARENA_RESULT_GAUNTLET_LOST
                                  ? COMPOUND_STRING("Lost to ") : COMPOUND_STRING("Quit before "));
            end = StringCopy(end, GetTrainerNameFromId(sArena.resultTrainer));
            end = StringCopy(end, COMPOUND_STRING(": beat "));
            end = AppendNumber(end, sArena.fight);
            end = StringCopy(end, COMPOUND_STRING("/"));
            end = AppendNumber(end, GetEntryFightCount(GetCurrentEntry()));
            end = StringCopy(end, COMPOUND_STRING(", ¥"));
            AppendNumber(end, sArena.runPrize);
            break;
        case ARENA_RESULT_NONE:
        default:
            StringCopy(dst, COMPOUND_STRING("Pick a battle."));
            break;
        }
        break;
    }
}

// Footer line 2: controls, or the last fight of a gauntlet.
static void BufferFooterHint(u8 *dst)
{
    u8 *end;

    switch (sArena.screen)
    {
    case ARENA_SCREEN_STARTER:
        StringCopy(dst, COMPOUND_STRING("A: choose"));
        break;
    case ARENA_SCREEN_BATTLES:
        StringCopy(dst, COMPOUND_STRING("A: fight   B: change starter"));
        break;
    case ARENA_SCREEN_GAUNTLET:
        end = StringCopy(dst, COMPOUND_STRING("Beat "));
        end = StringCopy(end, GetTrainerNameFromId(sArena.resultTrainer));
        end = StringCopy(end, COMPOUND_STRING(" +¥"));
        end = AppendNumber(end, sArena.lastPrize);
        end = StringCopy(end, COMPOUND_STRING("   Run so far ¥"));
        AppendNumber(end, sArena.runPrize);
        break;
    }
}

// ---------------------------------------------------------------------------
// Drawing

static void ClampCursor(void)
{
    u32 count = GetRowCount();
    u8 *cursor = &sArena.cursor[sArena.screen];
    u8 *scroll = &sArena.scroll[sArena.screen];

    if (*cursor >= count)
        *cursor = count - 1;
    if (*cursor < *scroll)
        *scroll = *cursor;
    else if (*cursor >= *scroll + ROWS_VISIBLE)
        *scroll = *cursor - ROWS_VISIBLE + 1;
}

static void DrawArenaScreen(void)
{
    u8 text[TEXT_BUFFER_LEN];
    u32 i;
    u32 count = GetRowCount();

    ClampCursor();

    FillWindowPixelBuffer(WIN_TITLE, PIXEL_FILL(1));
    BufferTitle(text);
    AddTextPrinterParameterized3(WIN_TITLE, FONT_NORMAL, 2, 0, sColorsNormal, TEXT_SKIP_DRAW, text);
    CopyWindowToVram(WIN_TITLE, COPYWIN_GFX);

    FillWindowPixelBuffer(WIN_LIST, PIXEL_FILL(1));
    for (i = 0; i < ROWS_VISIBLE; i++)
    {
        u32 row = sArena.scroll[sArena.screen] + i;
        const u8 *colors;

        if (row >= count)
            break;

        colors = (row == sArena.cursor[sArena.screen]) ? sColorsSelected : sColorsNormal;
        if (colors == sColorsSelected)
            AddTextPrinterParameterized3(WIN_LIST, FONT_NORMAL, 0, i * ROW_HEIGHT, colors, TEXT_SKIP_DRAW, COMPOUND_STRING("▶"));
        BufferRowText(row, text);
        AddTextPrinterParameterized3(WIN_LIST, FONT_NORMAL, LIST_TEXT_X, i * ROW_HEIGHT, colors, TEXT_SKIP_DRAW, text);
    }
    CopyWindowToVram(WIN_LIST, COPYWIN_GFX);

    FillWindowPixelBuffer(WIN_FOOTER, PIXEL_FILL(1));
    BufferFooterStatus(text);
    AddTextPrinterParameterized3(WIN_FOOTER, FONT_NORMAL, 2, 0, sColorsNormal, TEXT_SKIP_DRAW, text);
    BufferFooterHint(text);
    AddTextPrinterParameterized3(WIN_FOOTER, FONT_NORMAL, 2, ROW_HEIGHT, sColorsHint, TEXT_SKIP_DRAW, text);
    CopyWindowToVram(WIN_FOOTER, COPYWIN_GFX);
}

static void VBlankCB_TestArena(void)
{
    TransferPlttBuffer();
}

static void CB2_InitArenaScreen(void)
{
    u32 i;

    switch (gMain.state)
    {
    case 0:
        SetVBlankCallback(NULL);
        SetHBlankCallback(NULL);
        ScanlineEffect_Stop();
        SetGpuReg(REG_OFFSET_DISPCNT, 0);
        SetGpuReg(REG_OFFSET_BG0HOFS, 0);
        SetGpuReg(REG_OFFSET_BG0VOFS, 0);
        SetGpuReg(REG_OFFSET_WIN0H, 0);
        SetGpuReg(REG_OFFSET_WIN0V, 0);
        SetGpuReg(REG_OFFSET_WININ, 0);
        SetGpuReg(REG_OFFSET_WINOUT, 0);
        SetGpuReg(REG_OFFSET_BLDCNT, 0);
        SetGpuReg(REG_OFFSET_BLDALPHA, 0);
        SetGpuReg(REG_OFFSET_BLDY, 0);
        SetGpuReg(REG_OFFSET_MOSAIC, 0);
        DmaFill16(3, 0, (void *)VRAM, VRAM_SIZE);
        DmaFill32(3, 0, (void *)OAM, OAM_SIZE);
        DmaFill16(3, 0, (void *)PLTT, PLTT_SIZE);
        ResetPaletteFade();
        ResetTasks();
        ResetSpriteData();
        FreeAllSpritePalettes();
        gMain.state++;
        break;
    case 1:
        ResetBgsAndClearDma3BusyFlags(0);
        InitBgsFromTemplates(0, sArenaBgTemplates, ARRAY_COUNT(sArenaBgTemplates));
        InitWindows(sArenaWindowTemplates);
        DeactivateAllTextPrinters();
        LoadPalette(sBackdropColor, BG_PLTT_ID(0), PLTT_SIZEOF(1));
        LoadPalette(gStandardMenuPalette, BG_PLTT_ID(15), PLTT_SIZE_4BPP);
        gMain.state++;
        break;
    case 2:
        for (i = WIN_TITLE; i <= WIN_FOOTER; i++)
            PutWindowTilemap(i);
        DrawArenaScreen();
        CopyBgTilemapBufferToVram(0);
        SetGpuReg(REG_OFFSET_DISPCNT, DISPCNT_MODE_0 | DISPCNT_OBJ_1D_MAP);
        ShowBg(0);
        BeginNormalPaletteFade(PALETTES_ALL, 0, 16, 0, RGB_BLACK);
        EnableInterrupts(INTR_FLAG_VBLANK);
        SetVBlankCallback(VBlankCB_TestArena);
        PlayBGM(MUS_B_FRONTIER);
        gMain.state = 0;
        SetMainCallback2(CB2_TestArena);
        break;
    }
}

// ---------------------------------------------------------------------------
// Battles

static void BeginArenaBattle(void)
{
    BeginNormalPaletteFade(PALETTES_ALL, 0, 0, 16, RGB_BLACK);
    SetMainCallback2(CB2_StartArenaBattle);
}

static void StartEntry(u32 entryIndex)
{
    const struct TestArenaEntry *entry = &sTestArenaEntries[entryIndex];

    sArena.entry = entryIndex;
    sArena.fight = 0;
    sArena.result = ARENA_RESULT_NONE;
    sArena.lastPrize = 0;
    sArena.runPrize = 0;

    ZeroPlayerPartyMons();
    CreateRandomMonWithIVs(&gPlayerParty[0], sTestArenaStarters[sArena.starter], entry->playerLevel, TEST_ARENA_IVS);
    CalculatePlayerPartyCount();

    ClearBag();
    if (entry->potions != 0)
        AddBagItem(ITEM_POTION, entry->potions);

    BeginArenaBattle();
}

static void CB2_StartArenaBattle(void)
{
    u16 trainerId;

    UpdatePaletteFade();
    if (gPaletteFade.active)
        return;

    trainerId = GetCurrentOpponent();

    SetVBlankCallback(NULL);
    FreeAllWindowBuffers();

    gBattleTypeFlags = BATTLE_TYPE_TRAINER;
    if (GetTrainerBattleType(trainerId) == TRAINER_BATTLE_TYPE_DOUBLES)
        gBattleTypeFlags |= BATTLE_TYPE_DOUBLE;

    InitTrainerBattleParameter();
    TRAINER_BATTLE_PARAM.opponentA = trainerId;
    ZeroEnemyPartyMons();
    CreateNPCTrainerParty(gParties[B_TRAINER_OPPONENT_A], trainerId);

    // There is no map to read the environment from, so the arena picks it.
    gBattleEnvironment = BATTLE_ENVIRONMENT_BUILDING;
    gIsTestArenaBattle = TRUE;

    sArena.moneyBeforeFight = GetMoney(&gSaveBlock1Ptr->money);
    gMain.savedCallback = CB2_ReturnFromArenaBattle;
    PlayMapChosenOrBattleBGM(MUS_NONE);
    SetMainCallback2(CB2_InitBattle);
}

static void CB2_ReturnFromArenaBattle(void)
{
    const struct TestArenaEntry *entry = GetCurrentEntry();
    bool32 won = (gBattleOutcome == B_OUTCOME_WON);
    u32 moneyNow = GetMoney(&gSaveBlock1Ptr->money);

    gIsTestArenaBattle = FALSE;
    sArena.resultTrainer = GetCurrentOpponent();
    sArena.lastPrize = (won && moneyNow > sArena.moneyBeforeFight) ? moneyNow - sArena.moneyBeforeFight : 0;
    sArena.runPrize += sArena.lastPrize;

    if (!IsGauntlet(entry))
    {
        sArena.result = won ? ARENA_RESULT_WON : ARENA_RESULT_LOST;
        sArena.screen = ARENA_SCREEN_BATTLES;
    }
    else if (!won)
    {
        sArena.result = ARENA_RESULT_GAUNTLET_LOST;
        sArena.screen = ARENA_SCREEN_BATTLES;
    }
    else if (sArena.fight + 1 >= GetEntryFightCount(entry))
    {
        sArena.result = ARENA_RESULT_GAUNTLET_CLEARED;
        sArena.screen = ARENA_SCREEN_BATTLES;
    }
    else
    {
        sArena.fight++;
        sArena.result = ARENA_RESULT_WON;
        sArena.screen = ARENA_SCREEN_GAUNTLET;
        sArena.cursor[ARENA_SCREEN_GAUNTLET] = GAUNTLET_ROW_FIGHT;
    }

    gMain.state = 0;
    SetMainCallback2(CB2_InitArenaScreen);
}

// ---------------------------------------------------------------------------
// Input

static void TryUsePotion(void)
{
    // ExecuteTableBasedItemEffect returns TRUE when the item had no effect.
    if (!CheckBagHasItem(ITEM_POTION, 1)
     || ExecuteTableBasedItemEffect(&gPlayerParty[0], ITEM_POTION, 0, 0))
    {
        PlaySE(SE_FAILURE);
        return;
    }
    RemoveBagItem(ITEM_POTION, 1);
    PlaySE(SE_USE_ITEM);
}

static void SelectRow(u32 row)
{
    switch (sArena.screen)
    {
    case ARENA_SCREEN_STARTER:
        PlaySE(SE_SELECT);
        sArena.starter = row;
        sArena.result = ARENA_RESULT_NONE;
        sArena.screen = ARENA_SCREEN_BATTLES;
        DrawArenaScreen();
        break;
    case ARENA_SCREEN_BATTLES:
        PlaySE(SE_SELECT);
        StartEntry(row);
        break;
    case ARENA_SCREEN_GAUNTLET:
        switch (row)
        {
        case GAUNTLET_ROW_FIGHT:
            PlaySE(SE_SELECT);
            BeginArenaBattle();
            break;
        case GAUNTLET_ROW_POTION:
            TryUsePotion();
            DrawArenaScreen();
            break;
        case GAUNTLET_ROW_GIVE_UP:
            PlaySE(SE_SELECT);
            sArena.resultTrainer = GetCurrentOpponent();
            sArena.result = ARENA_RESULT_GAUNTLET_QUIT;
            sArena.screen = ARENA_SCREEN_BATTLES;
            DrawArenaScreen();
            break;
        }
        break;
    }
}

static void HandleArenaInput(void)
{
    u32 count = GetRowCount();
    u8 *cursor = &sArena.cursor[sArena.screen];

    if (JOY_REPEAT(DPAD_UP))
    {
        PlaySE(SE_SELECT);
        *cursor = (*cursor == 0) ? count - 1 : *cursor - 1;
        DrawArenaScreen();
    }
    else if (JOY_REPEAT(DPAD_DOWN))
    {
        PlaySE(SE_SELECT);
        *cursor = (*cursor + 1 >= count) ? 0 : *cursor + 1;
        DrawArenaScreen();
    }
    else if (JOY_NEW(A_BUTTON))
    {
        SelectRow(*cursor);
    }
    else if (JOY_NEW(B_BUTTON) && sArena.screen == ARENA_SCREEN_BATTLES)
    {
        PlaySE(SE_SELECT);
        sArena.screen = ARENA_SCREEN_STARTER;
        DrawArenaScreen();
    }
}

static void CB2_TestArena(void)
{
    UpdatePaletteFade();
    if (!gPaletteFade.active)
        HandleArenaInput();
}

// ---------------------------------------------------------------------------
// Boot

void TestArena_StartFromBoot(void)
{
    // A throwaway game in RAM only: nothing in the arena ever saves.
    NewGameInitData();
    gSaveBlock2Ptr->playerGender = MALE;
    StringCopy_PlayerName(gSaveBlock2Ptr->playerName, COMPOUND_STRING("TESTER"));
    gSaveBlock2Ptr->optionsTextSpeed = OPTIONS_TEXT_SPEED_FAST;
    gSaveBlock2Ptr->optionsBattleStyle = OPTIONS_BATTLE_STYLE_SET;

    memset(&sArena, 0, sizeof(sArena));
    sArena.screen = ARENA_SCREEN_STARTER;
    gIsTestArenaBattle = FALSE;

    gMain.state = 0;
    SetMainCallback2(CB2_InitArenaScreen);
}
