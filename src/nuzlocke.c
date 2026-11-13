#include "global.h"
#include "battle.h"
#include "event_data.h"
#include "main.h"
#include "nuzlocke.h"
#include "overworld.h"
#include "pokedex.h"
#include "pokemon.h"
#include "pokemon_storage_system.h"
#include "string_util.h"
#include "constants/pokedex.h"
#include "constants/region_map_sections.h"

// Nuzlocke rules. See the B_NUZLOCKE settings in include/config/battle.h.

STATIC_ASSERT(MAPSEC_COUNT <= 8 * sizeof(((struct SaveBlock1 *)0)->nuzlockeAreasUsed), NuzlockeAreaBitsFit);
STATIC_ASSERT(B_NUZLOCKE_GRAVEYARD_BOX < TOTAL_BOXES_COUNT, NuzlockeGraveyardBoxExists);

static const u8 sText_GraveyardBoxName[] = _("GRAVES");

// TRUE while a battle started from a wild encounter in the overworld
// (grass, surfing, fishing, Rock Smash, Sweet Scent, Safari Zone) is running.
static EWRAM_DATA bool8 sIsAreaEncounter = FALSE;

// Pokémon buried after the last battle. Battles with a partner (Steven) save the
// party first and the script loads it back afterwards, so those Pokémon have to be
// removed from the loaded party too (see Nuzlocke_OnPlayerPartyLoaded).
static EWRAM_DATA u32 sBuriedPersonalities[PARTY_SIZE] = {0};
static EWRAM_DATA u8 sBuriedCount = 0;

bool32 Nuzlocke_IsGraveyardBox(u32 boxId)
{
    return B_NUZLOCKE && boxId == B_NUZLOCKE_GRAVEYARD_BOX;
}

void Nuzlocke_InitNewGame(void)
{
    if (B_NUZLOCKE)
        StringCopy(GetBoxNamePtr(B_NUZLOCKE_GRAVEYARD_BOX), sText_GraveyardBoxName);
}

void Nuzlocke_SetAreaEncounter(bool32 isAreaEncounter)
{
    sIsAreaEncounter = isAreaEncounter;
}

static bool32 IsAreaUsed(u32 mapsec)
{
    if (mapsec >= MAPSEC_COUNT)
        return FALSE;
    return (gSaveBlock1Ptr->nuzlockeAreasUsed[mapsec / 8] >> (mapsec % 8)) & 1;
}

static void SetAreaUsed(u32 mapsec)
{
    if (mapsec < MAPSEC_COUNT)
        gSaveBlock1Ptr->nuzlockeAreasUsed[mapsec / 8] |= 1 << (mapsec % 8);
}

static bool32 IsCurrentAreaUsed(void)
{
    return IsAreaUsed(gMapHeader.regionMapSectionId);
}

static enum Species GetFamilyBaseSpecies(enum Species species)
{
    enum Species preEvolution;
    u32 i;

    for (i = 0; i < 3; i++)
    {
        preEvolution = GetSpeciesPreEvolution(species);
        if (preEvolution == SPECIES_NONE)
            break;
        species = preEvolution;
    }
    return species;
}

static bool32 IsFamilyMemberCaught(enum Species species, u32 depth)
{
    const struct Evolution *evolutions;
    u32 i;

    if (GetSetPokedexFlag(SpeciesToNationalPokedexNum(species), FLAG_GET_CAUGHT))
        return TRUE;
    if (depth >= 3)
        return FALSE;

    evolutions = GetSpeciesEvolutions(species);
    if (evolutions == NULL)
        return FALSE;
    for (i = 0; evolutions[i].method != EVOLUTIONS_END; i++)
    {
        if (evolutions[i].targetSpecies != species && IsFamilyMemberCaught(evolutions[i].targetSpecies, depth + 1))
            return TRUE;
    }
    return FALSE;
}

// A Pokémon is a duplicate if any member of its evolution family has been caught.
bool32 Nuzlocke_IsDupe(enum Species species)
{
    if (!B_NUZLOCKE || !B_NUZLOCKE_DUPES_CLAUSE || species == SPECIES_NONE)
        return FALSE;
    return IsFamilyMemberCaught(GetFamilyBaseSpecies(species), 0);
}

// Dupes clause: an area's first encounter shouldn't be a Pokémon you already have.
bool32 Nuzlocke_ShouldRerollWildMon(enum Species species)
{
    if (!B_NUZLOCKE || !B_NUZLOCKE_ONE_CATCH_PER_AREA || !B_NUZLOCKE_DUPES_CLAUSE)
        return FALSE;
    return !IsCurrentAreaUsed() && Nuzlocke_IsDupe(species);
}

bool32 Nuzlocke_CanCatchWildMon(struct Pokemon *mon)
{
    if (!B_NUZLOCKE || !B_NUZLOCKE_ONE_CATCH_PER_AREA || !sIsAreaEncounter)
        return TRUE;
    if (B_NUZLOCKE_SHINY_CLAUSE && IsMonShiny(mon))
        return TRUE;
    if (IsCurrentAreaUsed())
        return FALSE;
    return !Nuzlocke_IsDupe(GetMonData(mon, MON_DATA_SPECIES));
}

// Revival items don't work on the player's Pokémon.
bool32 Nuzlocke_IsReviveBlocked(struct Pokemon *mon)
{
    return B_NUZLOCKE && mon >= &gParties[B_TRAINER_PLAYER][0] && mon < &gParties[B_TRAINER_PLAYER][PARTY_SIZE];
}

static void SendToGraveyard(struct Pokemon *mon)
{
    u32 i;

    if (sBuriedCount < PARTY_SIZE)
        sBuriedPersonalities[sBuriedCount++] = GetMonData(mon, MON_DATA_PERSONALITY);

    for (i = 0; i < IN_BOX_COUNT; i++)
    {
        struct BoxPokemon *slot = GetBoxedMonPtr(B_NUZLOCKE_GRAVEYARD_BOX, i);
        if (GetBoxMonData(slot, MON_DATA_SPECIES) == SPECIES_NONE)
        {
            CopyMon(slot, &mon->box, sizeof(mon->box));
            break;
        }
    }
    // If the graveyard is full, the Pokémon is simply lost.
    ZeroMonData(mon);
}

// Returns FALSE if the player has no Pokémon left that can battle.
static bool32 BuryFaintedPartyMons(void)
{
    bool32 anyAlive = FALSE;
    u32 i;

    for (i = 0; i < PARTY_SIZE; i++)
    {
        struct Pokemon *mon = &gParties[B_TRAINER_PLAYER][i];
        if (GetMonData(mon, MON_DATA_SPECIES) == SPECIES_NONE || GetMonData(mon, MON_DATA_IS_EGG))
            continue;
        if (GetMonData(mon, MON_DATA_HP) == 0)
            SendToGraveyard(mon);
        else
            anyAlive = TRUE;
    }
    CompactPartySlots();
    CalculatePlayerPartyCount();
    return anyAlive;
}

// Called at the end of every battle. Returns FALSE if the run is over.
bool32 Nuzlocke_AfterBattle(void)
{
    bool32 isAreaEncounter = sIsAreaEncounter;

    sIsAreaEncounter = FALSE;
    sBuriedCount = 0;
    if (!B_NUZLOCKE)
        return TRUE;
    // These use a borrowed or temporary party, or restore it afterwards (Secret Base and e-Reader battles are friendly).
    if (gBattleTypeFlags & (BATTLE_TYPE_LINK | BATTLE_TYPE_RECORDED | BATTLE_TYPE_FRONTIER | BATTLE_TYPE_CATCH_TUTORIAL
                          | BATTLE_TYPE_SECRET_BASE | BATTLE_TYPE_EREADER_TRAINER))
        return TRUE;

    if (B_NUZLOCKE_ONE_CATCH_PER_AREA && isAreaEncounter && !IsCurrentAreaUsed())
    {
        struct Pokemon *wildMon = &gParties[B_TRAINER_OPPONENT_A][0];
        enum Species species = GetMonData(wildMon, MON_DATA_SPECIES);
        bool32 isFreeShiny = B_NUZLOCKE_SHINY_CLAUSE && IsMonShiny(wildMon);

        if (species != SPECIES_NONE && !isFreeShiny)
        {
            // A catch is only possible when it counted, so it always uses the area.
            // Otherwise a duplicate doesn't use it up.
            if (gBattleOutcome == B_OUTCOME_CAUGHT || !Nuzlocke_IsDupe(species))
                SetAreaUsed(gMapHeader.regionMapSectionId);
        }
    }

    return BuryFaintedPartyMons();
}

// Called after LoadPlayerParty restores a party saved before a battle.
void Nuzlocke_OnPlayerPartyLoaded(void)
{
    u32 i, j;

    if (!B_NUZLOCKE || sBuriedCount == 0)
        return;
    for (i = 0; i < PARTY_SIZE; i++)
    {
        struct Pokemon *mon = &gParties[B_TRAINER_PLAYER][i];
        if (GetMonData(mon, MON_DATA_SPECIES) == SPECIES_NONE)
            continue;
        for (j = 0; j < sBuriedCount; j++)
        {
            if (GetMonData(mon, MON_DATA_PERSONALITY) == sBuriedPersonalities[j])
            {
                ZeroMonData(mon);
                break;
            }
        }
    }
    sBuriedCount = 0;
    CompactPartySlots();
    CalculatePlayerPartyCount();
}
