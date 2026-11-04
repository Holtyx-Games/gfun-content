--Add Playermodel
player_manager.AddValidModel( "Jack Skellington Fortnite", "models/player/jack_fn_pm.mdl" )
player_manager.AddValidHands( "Jack Skellington Fortnite", "models/weapons/jack_fn_hands.mdl" )

--Add NPC
local Category = "Fortnite"

--Friendly NPC
local NPC = 
{
    Name = "Jack Skellington - Friendly",
    Class = "npc_citizen",
	Model = "models/player/jack_fn_pm.mdl",
	Health = "100",
	KeyValues = { citizentype = 3 },
	Category = Category
}
list.Set( "NPC", "jack_fn_friendly", NPC )

local Category = "Fortnite"

--Hostile NPC
local NPC = 
{
    Name = "Jack Skellington - Hostile",
	Class = "npc_combine_s",
	Model = "models/player/jack_fn_pm.mdl",
	Health = "100",
	Category = Category
}
list.Set( "NPC", "jack_fn_hostile", NPC )