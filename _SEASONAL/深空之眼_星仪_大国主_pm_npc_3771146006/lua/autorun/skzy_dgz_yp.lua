--Add Playermodel
player_manager.AddValidModel( "星仪·大国主", "models/pm/x_skzy_xy_dgz_yp_pm.mdl" )                         --PM模型
player_manager.AddValidHands( "星仪·大国主", "models/arms/x_skzy_xy_dgz_yp_arms.mdl", 0, "00000000" )      --PM手模

local Category = "星仪·大国主"                                                                        --NPC MOD分类

local NPC = 
{
	Name = "星仪·大国主(Friendly)",                                                            --友好NPC名字
	Class = "npc_citizen", 
	Health = "150",                                                                    --NPC血量
	KeyValues = { citizentype = 4 }, 
	Model = "models/NPC/x_skzy_xy_dgz_yp_npc.mdl",                                                  --友好NPC模型
	Weapons = { "weapon_ar2","weapon_smg1"},                                           --NPC出生自带武器
	Category = Category
}

list.Set( "NPC", "x_skzy_xy_dgz_yp_npc_friendly", NPC )

local NPC =
{
	Name = "星仪·大国主(Enemy)",                                                                --敌人NPC名字
	Class = "npc_combine_s",
	Health = "150",
	Numgrenades = "4",
	Model = "models/NPC/x_skzy_xy_dgz_yp_npc.mdl",                                                  --敌人NPC模型
	Weapons = { "weapon_ar2","weapon_smg1"},
	Category = Category
}

list.Set( "NPC", "x_skzy_xy_dgz_yp_npc", NPC )
