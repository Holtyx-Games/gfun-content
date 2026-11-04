if SERVER then AddCSLuaFile() return end
-- Retire callbacks from the experimental cloth controller after Lua auto-refresh.
for ent,state in pairs(MyersGhostClothCallbacks or {}) do
 if IsValid(ent) and state.callback then ent:RemoveCallback("BuildBonePositions",state.callback) end
end
MyersGhostClothCallbacks=nil
MyersGhostClothSetup=nil
MyersGhostClothRebuild=nil
timer.Remove("MyersGhost.Cloth")
hook.Remove("OnEntityCreated","MyersGhost.Cloth")
