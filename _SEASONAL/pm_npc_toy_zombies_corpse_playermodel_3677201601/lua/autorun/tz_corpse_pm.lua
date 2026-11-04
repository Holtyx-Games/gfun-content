player_manager.AddValidModel( "Corpse TZ", "models/tz/player/corpse_tz.mdl" )


local Category = "Toy Zombies"


local NPC = 
{
    Name = "Corpse (Friendly)",
    Class = "npc_citizen",
	Model = "models/tz/player/corpse_tz_ally.mdl",
	Health = "100",
	KeyValues = { citizentype = 4 },
	Weapons = { "weapon_smg1", "weapon_ar2", "weapon_shotgun" },
    Category = Category
}
list.Set( "NPC", "npc_corpse_tz_ally", NPC )


local NPC = 
{
    Name = "Corpse (Hostile)",
	Class = "npc_combine_s",
	Model = "models/tz/player/corpse_tz_hostile.mdl",
	Health = "100",
	Weapons = { "weapon_smg1", "weapon_ar2", "weapon_shotgun" },
    Category = Category
}
list.Set( "NPC", "npc_corpse_tz_hostile", NPC )
