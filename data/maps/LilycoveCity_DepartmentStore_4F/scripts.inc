LilycoveCity_DepartmentStore_4F_MapScripts::
	.byte 0

LilycoveCity_DepartmentStore_4F_EventScript_Gentleman::
	msgbox LilycoveCity_DepartmentStore_4F_Text_AttackOrDefenseTM, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_4F_EventScript_Woman::
	msgbox LilycoveCity_DepartmentStore_4F_Text_FiftyDifferentTMs, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_4F_EventScript_Youngster::
	msgbox LilycoveCity_DepartmentStore_4F_Text_PokemonOnlyHaveFourMoves, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_4F_EventScript_ClerkLeft::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_4F_Pokemart_AttackTMs
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2
LilycoveCity_DepartmentStore_4F_Pokemart_AttackTMs:
	.2byte ITEM_TM_FIRE_BLAST
	.2byte ITEM_TM_THUNDER
	.2byte ITEM_TM_BLIZZARD
	.2byte ITEM_TM_HYPER_BEAM
	pokemartlistend

LilycoveCity_DepartmentStore_4F_EventScript_ClerkRight::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_4F_Pokemart_DefenseTMs
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2
LilycoveCity_DepartmentStore_4F_Pokemart_DefenseTMs:
	.2byte ITEM_TM_PROTECT
	.2byte ITEM_TM_SAFEGUARD
	.2byte ITEM_TM_REFLECT
	.2byte ITEM_TM_LIGHT_SCREEN
	pokemartlistend

LilycoveCity_DepartmentStore_4F_Text_AttackOrDefenseTM:
	.string "Hmm…\p"
	.string "An attacking move…\n"
	.string "Or a defensive move…\p"
	.string "It's no easy matter to decide which TM\n"
	.string "moves should be taught to POKéMON…$"

LilycoveCity_DepartmentStore_4F_Text_FiftyDifferentTMs:
	.string "There are so many different kinds of\n"
	.string "TM moves.\p"
	.string "A catalog I read said there are fifty\n"
	.string "different kinds.$"

LilycoveCity_DepartmentStore_4F_Text_PokemonOnlyHaveFourMoves:
	.string "I'd like to get all the different TMs,\n"
	.string "but a POKéMON learns only four moves.$"


@ Free move tutor: teaches a POKéMON any move it can learn in any game.
@ Every move is a tutor move (extraTutors in src/data/pokemon/special_movesets.json),
@ so the tutor move relearner lists all of them.
LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorClerk::
	lockall
	faceplayer
	msgbox LilycoveCity_DepartmentStore_4F_Text_MoveTutorIntro, MSGBOX_DEFAULT
	goto LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorChooseMon
	end

LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorChooseMon::
	msgbox LilycoveCity_DepartmentStore_4F_Text_MoveTutorWhichMon, MSGBOX_DEFAULT
	setmoverelearnerstate MOVE_RELEARNER_TUTOR_MOVES
	chooseboxmon SELECT_PC_MON_MOVE_RELEARNER
	waitstate
	goto_if_eq VAR_0x8004, PARTY_NOTHING_CHOSEN, LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorComeAgain
	special IsSelectedMonEgg
	goto_if_eq VAR_RESULT, TRUE, LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorCantTeachEgg
	special Special_HasMoveToRelearn
	goto_if_eq VAR_RESULT, FALSE, LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorNoMoves
	msgbox LilycoveCity_DepartmentStore_4F_Text_MoveTutorWhichMove, MSGBOX_DEFAULT
	special TeachMoveRelearnerMove
	goto LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorAnotherMon
	end

LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorAnotherMon::
	msgbox LilycoveCity_DepartmentStore_4F_Text_MoveTutorAnythingElse, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, YES, LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorChooseMon
	goto LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorComeAgain
	end

LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorCantTeachEgg::
	msgbox LilycoveCity_DepartmentStore_4F_Text_MoveTutorCantTeachEgg, MSGBOX_DEFAULT
	goto LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorAnotherMon
	end

LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorNoMoves::
	msgbox LilycoveCity_DepartmentStore_4F_Text_MoveTutorNoMoves, MSGBOX_DEFAULT
	goto LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorAnotherMon
	end

LilycoveCity_DepartmentStore_4F_EventScript_MoveTutorComeAgain::
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	releaseall
	end

LilycoveCity_DepartmentStore_4F_Text_MoveTutorIntro:
	.string "Welcome to the MOVE TUTOR counter!\p"
	.string "We can teach your POKéMON any move\n"
	.string "it's able to learn--free of charge!$"

LilycoveCity_DepartmentStore_4F_Text_MoveTutorWhichMon:
	.string "Which POKéMON should learn a move?$"

LilycoveCity_DepartmentStore_4F_Text_MoveTutorWhichMove:
	.string "Which move should it learn?$"

LilycoveCity_DepartmentStore_4F_Text_MoveTutorAnythingElse:
	.string "Would you like to teach another\n"
	.string "move?$"

LilycoveCity_DepartmentStore_4F_Text_MoveTutorCantTeachEgg:
	.string "I'm sorry, we can't teach moves\n"
	.string "to an EGG.$"

LilycoveCity_DepartmentStore_4F_Text_MoveTutorNoMoves:
	.string "That POKéMON already knows every\n"
	.string "move we could teach it.$"
