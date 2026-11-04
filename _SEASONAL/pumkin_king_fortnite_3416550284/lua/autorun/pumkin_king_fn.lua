--Add Playermodel
player_manager.AddValidModel( "Pumpking King - Fortnite", "models/player/pumpking_fn_pm.mdl" )
player_manager.AddValidHands( "Pumpking King - Fortnite", "models/weapons/pumpking_fn_hands.mdl" )
list.Set( "PlayerOptionsModel", "Pumpking King - Fortnite - Fortnite", "models/player/pumpking_fn_pm.mdl" )

--Add NPC
local Category = "Fortnite"

--Friendly NPC
local NPC = 
{
    Name = "Pumpking King - Friendly",
    Class = "npc_citizen",
	Model = "models/player/pumpking_fn_pm.mdl",
	Health = "100",
	KeyValues = { citizentype = 3 },
	Category = Category
}
list.Set( "NPC", "pumpking_fn_friendly", NPC )

local Category = "Fortnite"

--Hostile NPC
local NPC = 
{
    Name = "Pumpking King - Hostile",
	Class = "npc_combine_s",
	Model = "models/player/pumpking_fn_pm.mdl",
	Health = "100",
	Category = Category
}
list.Set( "NPC", "pumpking_fn_hostile", NPC )