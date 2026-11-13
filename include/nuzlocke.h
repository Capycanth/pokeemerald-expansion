#ifndef GUARD_NUZLOCKE_H
#define GUARD_NUZLOCKE_H

// Nuzlocke rules. See the B_NUZLOCKE settings in include/config/battle.h.

bool32 Nuzlocke_IsGraveyardBox(u32 boxId);
void Nuzlocke_InitNewGame(void);
bool32 Nuzlocke_IsDupe(enum Species species);
bool32 Nuzlocke_ShouldRerollWildMon(enum Species species);
bool32 Nuzlocke_CanCatchWildMon(struct Pokemon *mon);
bool32 Nuzlocke_IsReviveBlocked(struct Pokemon *mon);
bool32 Nuzlocke_AfterBattle(void);
void Nuzlocke_SetAreaEncounter(bool32 isAreaEncounter);
void Nuzlocke_OnPlayerPartyLoaded(void);

#endif // GUARD_NUZLOCKE_H
