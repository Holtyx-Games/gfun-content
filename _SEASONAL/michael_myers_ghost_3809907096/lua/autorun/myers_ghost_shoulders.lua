if SERVER then AddCSLuaFile() return end

local MODEL = "models/player/myers_ghost/myers_ghost.mdl"
local UP = Vector(0.98009837, -0.19749913, -0.02003515)
local SIDE = Vector(0.01805976, -0.01179824, 0.99976730)
for ent, state in pairs(_G.MyersSkinGhostShoulderCallbacks or {}) do
    if IsValid(ent) and state.callback then ent:RemoveCallback("BuildBonePositions", state.callback) end
end
local installed = setmetatable({}, {__mode = "k"})
_G.MyersSkinGhostShoulderCallbacks = installed

local function walking(ent)
    if ent:GetModel() ~= MODEL then return false end
    local seq = string.lower(ent:GetSequenceName(ent:GetSequence()) or "")
    for _, word in ipairs({"crouch", "cidle", "cwalk", "crun", "jump", "swim", "sit", "attack", "heavy", "grab", "victim", "death", "ragdoll"}) do
        if string.find(seq, word, 1, true) then return false end
    end
    if ent:IsPlayer() then
        if not ent:Alive() or ent:Crouching() or ent:InVehicle()
            or not ent:OnGround() or ent:WaterLevel() >= 2
            or ent:GetMoveType() ~= MOVETYPE_WALK then return false end
    end
    return ent:GetVelocity():Length2D() > 12
        or string.find(seq, "walk", 1, true) ~= nil
        or string.find(seq, "run", 1, true) ~= nil
        or string.find(seq, "rush", 1, true) ~= nil
end

local function chain(ent, root)
    local result = {}
    for bone = 0, ent:GetBoneCount() - 1 do
        local parent = bone
        for _ = 1, ent:GetBoneCount() do
            if parent == root then result[#result + 1] = bone break end
            if parent < 0 then break end
            parent = ent:GetBoneParent(parent)
        end
    end
    return result
end

local function setup(ent)
    local chest = ent:LookupBone("ValveBiped.Bip01_Spine4")
    if not chest then return end
    local shoulders = {}
    for _, side in ipairs({{"L", 1, 1.525774, 7.092269}, {"R", -1, 1.653047, 7.003522}}) do
        local arm = ent:LookupBone("ValveBiped.Bip01_" .. side[1] .. "_UpperArm")
        local clavicle = ent:LookupBone("ValveBiped.Bip01_" .. side[1] .. "_Clavicle")
        if not arm or not clavicle then return end
        shoulders[#shoulders + 1] = {arm = arm, clavicle = clavicle,
            sign = side[2], height = side[3], width = side[4] * 1.05,
            descendants = chain(ent, arm)}
    end
    return {chest = chest, shoulders = shoulders, blend = 0}
end

local function build(ent, count)
    local state = installed[ent]
    if not state or ent:GetModel() ~= MODEL or count < 1 then return end
    if state.frame ~= FrameNumber() then
        state.frame = FrameNumber()
        state.blend = math.Approach(state.blend, walking(ent) and 1 or 0, FrameTime() * 8)
    end
    if state.blend <= 0 then return end
    local chest = ent:GetBoneMatrix(state.chest)
    if not chest then return end
    local inverse = chest:GetInverse()
    if not inverse then return end
    -- Change translations in the freshly evaluated pose; no persistent bone
    -- manipulation, recursive SetupBones, or accumulated offsets.
    for _, shoulder in ipairs(state.shoulders) do
        local matrix = ent:GetBoneMatrix(shoulder.arm)
        if matrix then
            local current = matrix:GetTranslation()
            local localPos = inverse * current
            local lift = math.max(0, shoulder.height - localPos:Dot(UP))
            local widen = math.max(0, shoulder.width - localPos:Dot(SIDE) * shoulder.sign)
            local correction = UP * lift + SIDE * (widen * shoulder.sign)
            if correction:Length() > 3 then correction = correction:GetNormalized() * 3 end
            local delta = ((chest * (localPos + correction)) - current) * state.blend
            for _, bone in ipairs(shoulder.descendants) do
                local m = ent:GetBoneMatrix(bone)
                if m then m:SetTranslation(m:GetTranslation() + delta) ent:SetBoneMatrix(bone, m) end
            end
            local clavicle = ent:GetBoneMatrix(shoulder.clavicle)
            if clavicle then
                clavicle:SetTranslation(clavicle:GetTranslation() + delta * 0.5)
                ent:SetBoneMatrix(shoulder.clavicle, clavicle)
            end
        end
    end
end

timer.Create("MyersSkinGhost.ShoulderPosture", 0.5, 0, function()
    for ent, state in pairs(installed) do
        if not IsValid(ent) then installed[ent] = nil
        elseif ent:GetModel() ~= MODEL then
            ent:RemoveCallback("BuildBonePositions", state.callback)
            installed[ent] = nil
        end
    end
    for _, ent in ipairs(ents.FindByModel(MODEL)) do
        if not installed[ent] and ent:GetClass() ~= "prop_ragdoll" then
            local state = setup(ent)
            if state then
                installed[ent] = state
                state.callback = ent:AddCallback("BuildBonePositions", build)
            end
        end
    end
end)
