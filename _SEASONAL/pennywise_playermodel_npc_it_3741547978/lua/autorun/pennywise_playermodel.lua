-- Pennywise Playermodel + C_Arms + NPC Support
-- Put this file in: lua/autorun/pennywise_playermodel.lua

if SERVER then
    AddCSLuaFile()
end

local CATEGORY = "Pennywise"
local PM_NAME = "Pennywise"
local PM_MODEL = "models/player/pennywise.mdl"
local HANDS_MODEL = "models/weapons/c_arms_pennywise.mdl"

-- Playermodel
player_manager.AddValidModel(PM_NAME, PM_MODEL)
player_manager.AddValidHands(PM_NAME, HANDS_MODEL, 0, "00000000")

list.Set("PlayerOptionsModel", PM_NAME, PM_MODEL)
list.Set("PlayerOptionsAnimations", PM_NAME, { "menu_combine" })

-- Friendly NPC
list.Set("NPC", "npc_pennywise_friendly", {
    Name = "Pennywise Friendly",
    Class = "npc_citizen",
    Model = PM_MODEL,
    Health = "100",
    KeyValues = { citizentype = 4 },
    Category = CATEGORY
})

-- Hostile NPC
list.Set("NPC", "npc_pennywise_hostile", {
    Name = "Pennywise Hostile",
    Class = "npc_combine_s",
    Model = PM_MODEL,
    Health = "100",
    Weapons = { "weapon_smg1", "weapon_ar2", "weapon_shotgun" },
    Category = CATEGORY
})
