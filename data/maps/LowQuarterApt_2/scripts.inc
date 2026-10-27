@ Scene 2: The Apartment
@ Design doc: docs/scenes/scene-02-the-apartment.md (Pokemon ROM Hack project)
@
@ VAR_LOW_QUARTER_APT_STATE
@   0 = Scene 2 not played yet (plays on entry)
@   1 = Scene 2 done; Mom is in her bedroom
@
@ VAR_STARTER_CHOICE (read by the van scene)
@   STARTER_CHOICE_SPHEAL   (0) = "The bulky blubber-wall: Walrein"
@   STARTER_CHOICE_ROLYCOLY (1) = "The stoic steam engine: Coalossal"
@   STARTER_CHOICE_SEEDOT   (2) = "The nimble nightmare: Shiftry"

LowQuarterApt_2_MapScripts::
	map_script MAP_SCRIPT_ON_TRANSITION, LowQuarterApt_2_OnTransition
	map_script MAP_SCRIPT_ON_FRAME_TABLE, LowQuarterApt_2_OnFrame
	.byte 0

LowQuarterApt_2_OnTransition:
	@ The landlord only appears during Scene 2.
	setflag FLAG_TEMP_1
	call LowQuarterApt_2_EventScript_SetSiblingGfx
	call_if_ge VAR_LOW_QUARTER_APT_STATE, 1, LowQuarterApt_2_EventScript_SetAfterScene2
	end

@ The little sibling is always the opposite gender of the MC.
LowQuarterApt_2_EventScript_SetSiblingGfx::
	checkplayergender
	goto_if_eq VAR_RESULT, MALE, LowQuarterApt_2_EventScript_SetSisterGfx
	setvar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_WALLY
	return

LowQuarterApt_2_EventScript_SetSisterGfx::
	setvar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_GIRL_2
	return

LowQuarterApt_2_EventScript_SetAfterScene2::
	setobjectxyperm LOCALID_LOW_QUARTER_APT_MOM, 11, 9
	setobjectmovementtype LOCALID_LOW_QUARTER_APT_MOM, MOVEMENT_TYPE_FACE_DOWN
	setobjectmovementtype LOCALID_LOW_QUARTER_APT_SIBLING, MOVEMENT_TYPE_FACE_LEFT
	return

LowQuarterApt_2_OnFrame:
	map_script_2 VAR_LOW_QUARTER_APT_STATE, 0, LowQuarterApt_2_EventScript_Scene2
	.2byte 0

LowQuarterApt_2_EventScript_Scene2::
	lockall
@ Part 1: The Bedtime Story
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_PlayerToBedroomDoor
	waitmovement 0
	msgbox LowQuarterApt_2_Text_ItsCold, MSGBOX_DEFAULT
	msgbox LowQuarterApt_2_Text_HeatersActingUp, MSGBOX_DEFAULT
	msgbox LowQuarterApt_2_Text_Okay, MSGBOX_DEFAULT
	msgbox LowQuarterApt_2_Text_JettCalloway, MSGBOX_DEFAULT
	closemessage
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_PlayerToBedside
	waitmovement 0
@ Part 2: Starter Choice
	dynmultichoice 1, 1, TRUE, 3, 0, DYN_MULTICHOICE_CB_NONE, LowQuarterApt_2_Text_ChoiceWalrein, LowQuarterApt_2_Text_ChoiceCoalossal, LowQuarterApt_2_Text_ChoiceShiftry
	copyvar VAR_STARTER_CHOICE, VAR_RESULT
	call_if_eq VAR_STARTER_CHOICE, STARTER_CHOICE_SPHEAL, LowQuarterApt_2_EventScript_BufferWalrein
	call_if_eq VAR_STARTER_CHOICE, STARTER_CHOICE_ROLYCOLY, LowQuarterApt_2_EventScript_BufferCoalossal
	call_if_eq VAR_STARTER_CHOICE, STARTER_CHOICE_SEEDOT, LowQuarterApt_2_EventScript_BufferShiftry
	applymovement LOCALID_LOW_QUARTER_APT_MOM, Common_Movement_FaceRight
	waitmovement 0
	msgbox LowQuarterApt_2_Text_DidntHearYouComeIn, MSGBOX_DEFAULT
	closemessage
	applymovement LOCALID_LOW_QUARTER_APT_MOM, Common_Movement_FaceLeft
	waitmovement 0
	msgbox LowQuarterApt_2_Text_WantToHearAboutJett, MSGBOX_DEFAULT
	msgbox LowQuarterApt_2_Text_Achoo, MSGBOX_DEFAULT
	closemessage
	applymovement LOCALID_LOW_QUARTER_APT_SIBLING, Common_Movement_FaceLeft
	waitmovement 0
	msgbox LowQuarterApt_2_Text_ILoveYou, MSGBOX_DEFAULT
	closemessage
@ Part 3: The Kitchen
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_PlayerToKitchen
	applymovement LOCALID_LOW_QUARTER_APT_MOM, LowQuarterApt_2_Movement_MomToStove
	waitmovement 0
	msgbox LowQuarterApt_2_Text_LeftoverSoup, MSGBOX_DEFAULT
	closemessage
	call LowQuarterApt_2_EventScript_BangOnDoor
	applymovement LOCALID_LOW_QUARTER_APT_MOM, LowQuarterApt_2_Movement_MomStartled
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_Startled
	waitmovement 0
	clearflag FLAG_TEMP_1
	addobject LOCALID_LOW_QUARTER_APT_LANDLORD
	playse SE_DOOR
	applymovement LOCALID_LOW_QUARTER_APT_LANDLORD, LowQuarterApt_2_Movement_LandlordEnter
	waitmovement 0
	msgbox LowQuarterApt_2_Text_ChaseRent, MSGBOX_DEFAULT
	closemessage
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_PlayerConfrontLandlord
	waitmovement 0
	checkplayergender
	call_if_eq VAR_RESULT, MALE, LowQuarterApt_2_EventScript_SisterAsleep
	call_if_eq VAR_RESULT, FEMALE, LowQuarterApt_2_EventScript_BrotherAsleep
	closemessage
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_PlayerPushedAside
	applymovement LOCALID_LOW_QUARTER_APT_LANDLORD, LowQuarterApt_2_Movement_LandlordToMom
	waitmovement 0
	applymovement LOCALID_LOW_QUARTER_APT_MOM, Common_Movement_FaceDown
	waitmovement 0
	msgbox LowQuarterApt_2_Text_PayOrCurb, MSGBOX_DEFAULT
	msgbox LowQuarterApt_2_Text_DontHaveItYet, MSGBOX_DEFAULT
	msgbox LowQuarterApt_2_Text_EndOfTheWeek, MSGBOX_DEFAULT
	closemessage
	applymovement LOCALID_LOW_QUARTER_APT_LANDLORD, LowQuarterApt_2_Movement_LandlordSniff
	waitmovement 0
	msgbox LowQuarterApt_2_Text_IsThatSoup, MSGBOX_DEFAULT
	closemessage
	applymovement LOCALID_LOW_QUARTER_APT_MOM, LowQuarterApt_2_Movement_MomPushedAside
	applymovement LOCALID_LOW_QUARTER_APT_LANDLORD, Common_Movement_WalkUp
	waitmovement 0
	msgbox LowQuarterApt_2_Text_OffYourTab, MSGBOX_DEFAULT
	closemessage
	applymovement LOCALID_LOW_QUARTER_APT_LANDLORD, LowQuarterApt_2_Movement_LandlordLeave
	waitmovement 0
	playse SE_EXIT
	removeobject LOCALID_LOW_QUARTER_APT_LANDLORD
@ Part 4: Aftermath
	applymovement LOCALID_LOW_QUARTER_APT_MOM, LowQuarterApt_2_Movement_MomLooksDownThenRight
	waitmovement 0
	msgbox LowQuarterApt_2_Text_SorryYouSawThat, MSGBOX_DEFAULT
	closemessage
	applymovement LOCALID_LOW_QUARTER_APT_MOM, LowQuarterApt_2_Movement_MomToBedroom
	waitmovement 0
	applymovement OBJ_EVENT_ID_PLAYER, LowQuarterApt_2_Movement_PlayerToDoor
	waitmovement 0
	setvar VAR_LOW_QUARTER_APT_STATE, 1
	@ TODO: the van scene goes here (the starter runs into the MC outside). Until it exists,
	@ the MC gets the starter here and goes straight into the Underground Ladder's battles,
	@ which have no map of their own yet.
	call LowQuarterApt_2_EventScript_GiveStarter
	call EventScript_UndergroundLadder
	@ TODO: the apartment door has no outdoor map yet, so for now this uses the door's own
	@ warp, which leads back into the apartment.
	warp MAP_LOW_QUARTER_APT_2, 0
	waitstate
	releaseall
	end

LowQuarterApt_2_EventScript_BufferWalrein::
	bufferspeciesname STR_VAR_1, SPECIES_WALREIN
	return

LowQuarterApt_2_EventScript_BufferCoalossal::
	bufferspeciesname STR_VAR_1, SPECIES_COALOSSAL
	return

LowQuarterApt_2_EventScript_BufferShiftry::
	bufferspeciesname STR_VAR_1, SPECIES_SHIFTRY
	return

@ Placeholder until the van scene: gives the first stage of the partner named in the
@ bedtime story at Lv 5, plus the ladder's one Potion.
LowQuarterApt_2_EventScript_GiveStarter::
	call_if_eq VAR_STARTER_CHOICE, STARTER_CHOICE_SPHEAL, LowQuarterApt_2_EventScript_GiveSpheal
	call_if_eq VAR_STARTER_CHOICE, STARTER_CHOICE_ROLYCOLY, LowQuarterApt_2_EventScript_GiveRolycoly
	call_if_eq VAR_STARTER_CHOICE, STARTER_CHOICE_SEEDOT, LowQuarterApt_2_EventScript_GiveSeedot
	additem ITEM_POTION
	playfanfare MUS_OBTAIN_ITEM
	msgbox LowQuarterApt_2_Text_GotStarter, MSGBOX_DEFAULT
	waitfanfare
	closemessage
	return

LowQuarterApt_2_EventScript_GiveSpheal::
	givemon SPECIES_SPHEAL, 5
	bufferspeciesname STR_VAR_1, SPECIES_SPHEAL
	return

LowQuarterApt_2_EventScript_GiveRolycoly::
	givemon SPECIES_ROLYCOLY, 5
	bufferspeciesname STR_VAR_1, SPECIES_ROLYCOLY
	return

LowQuarterApt_2_EventScript_GiveSeedot::
	givemon SPECIES_SEEDOT, 5
	bufferspeciesname STR_VAR_1, SPECIES_SEEDOT
	return

LowQuarterApt_2_EventScript_BangOnDoor::
	playse SE_BANG
	waitse
	delay 10
	playse SE_BANG
	waitse
	delay 10
	playse SE_BANG
	waitse
	delay 20
	return

LowQuarterApt_2_EventScript_SisterAsleep::
	msgbox LowQuarterApt_2_Text_LittleSistersAsleep, MSGBOX_DEFAULT
	return

LowQuarterApt_2_EventScript_BrotherAsleep::
	msgbox LowQuarterApt_2_Text_LittleBrothersAsleep, MSGBOX_DEFAULT
	return

@ (14, 11) -> (3, 7), facing the sibling's bedroom door
LowQuarterApt_2_Movement_PlayerToBedroomDoor:
	walk_up
	walk_up
	walk_up
	walk_up
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	face_down
	step_end

@ (3, 7) -> (3, 9), facing Mom
LowQuarterApt_2_Movement_PlayerToBedside:
	walk_down
	walk_down
	face_left
	step_end

@ (3, 9) -> (6, 4)
LowQuarterApt_2_Movement_PlayerToKitchen:
	walk_up
	walk_up
	walk_up
	walk_up
	walk_right
	walk_right
	walk_right
	walk_up
	face_right
	step_end

@ (2, 9) -> (2, 2), one step behind the MC so they don't overlap in the doorway
LowQuarterApt_2_Movement_MomToStove:
	delay_16
	walk_right
	walk_up
	walk_up
	walk_up
	walk_up
	walk_up
	walk_up
	walk_left
	walk_up
	step_end

LowQuarterApt_2_Movement_MomStartled:
	face_right
	emote_exclamation_mark
	step_end

LowQuarterApt_2_Movement_Startled:
	emote_exclamation_mark
	step_end

@ (14, 11) -> (14, 5)
LowQuarterApt_2_Movement_LandlordEnter:
	walk_up
	walk_up
	walk_up
	walk_up
	walk_up
	walk_up
	face_left
	step_end

@ (6, 4) -> (13, 5). Running is off for the MC's sprite, so this is a fast walk.
LowQuarterApt_2_Movement_PlayerConfrontLandlord:
	walk_fast_down
	walk_fast_right
	walk_fast_right
	walk_fast_right
	walk_fast_right
	walk_fast_right
	walk_fast_right
	walk_fast_right
	face_right
	step_end

@ (13, 5) -> (13, 4), shoved backward while facing down
LowQuarterApt_2_Movement_PlayerPushedAside:
	face_down
	lock_facing_direction
	walk_up
	unlock_facing_direction
	step_end

@ (14, 5) -> (2, 3), facing Mom at the stove
LowQuarterApt_2_Movement_LandlordToMom:
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_left
	walk_up
	walk_up
	walk_left
	face_up
	step_end

LowQuarterApt_2_Movement_LandlordSniff:
	face_down
	delay_16
	delay_16
	face_up
	step_end

@ (2, 2) -> (1, 2), shoved away from the stove while facing right
LowQuarterApt_2_Movement_MomPushedAside:
	face_right
	lock_facing_direction
	walk_left
	unlock_facing_direction
	step_end

@ (2, 2) -> (14, 11)
LowQuarterApt_2_Movement_LandlordLeave:
	walk_down
	walk_right
	walk_down
	walk_down
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_down
	walk_down
	walk_down
	walk_down
	walk_down
	walk_down
	step_end

LowQuarterApt_2_Movement_MomLooksDownThenRight:
	face_down
	delay_16
	delay_16
	face_right
	step_end

@ (1, 2) -> (11, 9), through the bedroom door at (9, 8)
LowQuarterApt_2_Movement_MomToBedroom:
	walk_down
	walk_right
	walk_right
	walk_down
	walk_down
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_right
	walk_down
	walk_down
	walk_down
	walk_down
	walk_right
	walk_right
	step_end

@ (13, 4) -> (14, 11)
LowQuarterApt_2_Movement_PlayerToDoor:
	walk_right
	walk_down
	walk_down
	walk_down
	walk_down
	walk_down
	walk_down
	walk_down
	step_end

LowQuarterApt_2_Text_ItsCold:
	.string "Brrr… it's cold in here, Mom. Can't we\n"
	.string "turn up the heat?$"

LowQuarterApt_2_Text_HeatersActingUp:
	.string "The heater's acting up again, sweetie…\p"
	.string "I'll grab you another blanket in a\n"
	.string "second.\p"
	.string "How about a bedtime story first?$"

LowQuarterApt_2_Text_Okay:
	.string "Okay…$"

LowQuarterApt_2_Text_JettCalloway:
	.string "How about that old story about Jett\n"
	.string "Calloway and his partner… uh…\p"
	.string "(Which Pokémon was it again?)$"

LowQuarterApt_2_Text_ChoiceWalrein:
	.string "The bulky blubber-wall: Walrein$"

LowQuarterApt_2_Text_ChoiceCoalossal:
	.string "The stoic steam engine: Coalossal$"

LowQuarterApt_2_Text_ChoiceShiftry:
	.string "The nimble nightmare: Shiftry$"

LowQuarterApt_2_Text_DidntHearYouComeIn:
	.string "Oh! {PLAYER}! I didn't hear you come in.\n"
	.string "That's right, it was {STR_VAR_1}!$"

LowQuarterApt_2_Text_WantToHearAboutJett:
	.string "Want to hear about Jett and {STR_VAR_1}?$"

LowQuarterApt_2_Text_Achoo:
	.string "ACHOO! Uh, I'm not feeling well, Mom.\n"
	.string "I think I'll just go to bed.$"

LowQuarterApt_2_Text_ILoveYou:
	.string "Oh… Sure… Well, I love you.\n"
	.string "*kisses head*$"

LowQuarterApt_2_Text_LeftoverSoup:
	.string "I'll heat you up some leftover soup.\n"
	.string "How did the ceremony go?\p"
	.string "…Oh, honey.\p"
	.string "Milo won? Well… good for the Fenwicks.\n"
	.string "They needed it as much as we did.$"

LowQuarterApt_2_Text_ChaseRent:
	.string "This is the second time I've had to come\n"
	.string "down here and chase rent!\p"
	.string "You're really testing my patience.$"

LowQuarterApt_2_Text_LittleSistersAsleep:
	.string "What?… So what if your little sister's\n"
	.string "asleep?\p"
	.string "If I don't get my rent, she'll be\n"
	.string "sleeping on the street soon enough.$"

LowQuarterApt_2_Text_LittleBrothersAsleep:
	.string "What?… So what if your little brother's\n"
	.string "asleep?\p"
	.string "If I don't get my rent, he'll be sleeping\n"
	.string "on the street soon enough.$"

LowQuarterApt_2_Text_PayOrCurb:
	.string "You think I like doing this?\n"
	.string "I've got bills too.\p"
	.string "So, what'll it be? Pay the rent or get\n"
	.string "kicked to the curb?$"

LowQuarterApt_2_Text_DontHaveItYet:
	.string "Well… I just don't have it yet…\p"
	.string "Tips were slow this week, but with all\n"
	.string "the graduation parties, they're bound\l"
	.string "to pick up!\p"
	.string "I'll pay you as soon as I can, I promise!$"

LowQuarterApt_2_Text_EndOfTheWeek:
	.string "*grumbles* You have until the end of\n"
	.string "the week. ¥1000, not a coin less!$"

LowQuarterApt_2_Text_IsThatSoup:
	.string "*sniff* *sniff* …Is that soup?$"

LowQuarterApt_2_Text_OffYourTab:
	.string "Tell you what. I'll take it off your tab.\n"
	.string "¥950.$"

LowQuarterApt_2_Text_SorryYouSawThat:
	.string "… Sorry you had to see that, {PLAYER}…\p"
	.string "You, uh, might have to find your own\n"
	.string "dinner tonight.\p"
	.string "Maybe your cousin can spare something?$"

@ Placeholder until the van scene
LowQuarterApt_2_Text_GotStarter:
	.string "{STR_VAR_1} joined your team!\n"
	.string "You got 1 Potion.$"
