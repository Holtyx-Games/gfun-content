if SERVER then AddCSLuaFile() end
local name = "Michael Myers - Ghost (Halloween)"
local model = "models/player/myers_ghost/myers_ghost.mdl"
player_manager.AddValidModel(name, model)
player_manager.AddValidHands(name, "models/player/myers_ghost/myers_ghost_hands.mdl", 0, "00000000")
list.Set("PlayerOptionsModel", name, model)
