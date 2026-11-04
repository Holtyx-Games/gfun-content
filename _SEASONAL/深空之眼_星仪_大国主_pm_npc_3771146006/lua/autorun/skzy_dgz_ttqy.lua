--Add Playermodel
player_manager.AddValidModel( "大国主「兔兔奇遇」", "models/pm/x_skzy_xy_dgz_ttqy_pm.mdl" )                         --PM模型
player_manager.AddValidHands( "大国主「兔兔奇遇」", "models/arms/x_skzy_xy_dgz_ttqy_arms.mdl", 0, "00000000" )      --PM手模

local Category = "大国主「兔兔奇遇」"                                                                        --NPC MOD分类

local NPC = 
{
	Name = "大国主「兔兔奇遇」(Friendly)",                                                            --友好NPC名字
	Class = "npc_citizen", 
	Health = "150",                                                                    --NPC血量
	KeyValues = { citizentype = 4 }, 
	Model = "models/NPC/x_skzy_xy_dgz_ttqy_npc.mdl",                                                  --友好NPC模型
	Weapons = { "weapon_ar2","weapon_smg1"},                                           --NPC出生自带武器
	Category = Category
}

list.Set( "NPC", "x_skzy_xy_dgz_ttqy_npc_friendly", NPC )

local NPC =
{
	Name = "大国主「兔兔奇遇」(Enemy)",                                                                --敌人NPC名字
	Class = "npc_combine_s",
	Health = "150",
	Numgrenades = "4",
	Model = "models/NPC/x_skzy_xy_dgz_ttqy_npc.mdl",                                                  --敌人NPC模型
	Weapons = { "weapon_ar2","weapon_smg1"},
	Category = Category
}

list.Set( "NPC", "x_skzy_xy_dgz_ttqy_npc", NPC )
