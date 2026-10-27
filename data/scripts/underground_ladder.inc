@ The Underground Ladder: eight single battles, Lv 3 -> 10, fought back to back.
@ Design doc: docs/battles.md (Pokemon ROM Hack project)
@
@ - No healing between fights. The player's only heal is one Potion, used from the Bag in battle.
@ - Prizes are fixed per trainer and paid by GetLadderPrize() (src/battle_script_commands.c).
@ - Losing a fight ends the ladder (goto Finish) without whiting out (FLAG_NO_WHITEOUT).
@   The party is not healed.
@
@ No map yet: the battles start straight from whatever map calls this. Use `call`;
@ the script returns once the ladder is cleared or lost.

EventScript_UndergroundLadder::
	@ No trainer objects: keep the no-intro battle's reveal step from moving whoever was last talked to.
	setvar VAR_LAST_TALKED, LOCALID_NONE
	setflag FLAG_NO_WHITEOUT
	trainerbattle_no_intro TRAINER_LADDER_TESSA, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_ROWAN, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_CLARA, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_FELIX, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_NADIA, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_HUGO, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_IVY, UndergroundLadder_Text_Defeat
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_ne VAR_RESULT, B_OUTCOME_WON, UndergroundLadder_EventScript_Finish
	trainerbattle_no_intro TRAINER_LADDER_SILAS, UndergroundLadder_Text_Defeat
UndergroundLadder_EventScript_Finish::
	clearflag FLAG_NO_WHITEOUT
	return

@ Placeholder: one shared line for all eight trainers until each gets their own.
UndergroundLadder_Text_Defeat:
	.string "You win this round.$"
