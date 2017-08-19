local acs_modpath = "/mods/additionalCameraStuff/"
local CM = import('/lua/ui/game/commandmode.lua')
local Decal = import('/lua/user/userdecal.lua').UserDecal

local ACSdata = {
    isPreviewAlive = false,
    previews = {
        buildrange = false,
        attackrange = false,
    },
    rings = {
        buildrange = {},
        attackrange = {},
    },
}

function isAcceptablePreviewMode(mode)
    if (not mode[2]) then
        return true
    end
    if (mode[1] == "order") then
        for _, s in {"RULEUCC_Move"} do
            if (mode[2].name == s) then
                return true
            end
        end
    end
    return false
end

function createRangeRingPreviews(units)
    -- buildrange
    units = units or {}
    if ACSdata.previews.buildrange then
        for _, u in EntityCategoryFilterDown(categories.ENGINEER, units) do
            local bp = u:GetBlueprint()
            local radius = bp.Economy.MaxBuildDistance
            if radius then
                if (not ACSdata.rings.buildrange[radius]) then
                    local texture = acs_modpath..'textures/range_ring.dds'
                    createRing(ACSdata.rings.buildrange, texture, radius, 2, 2, 2, 2)
                end
            end
        end
    end
    -- attackrange
    if ACSdata.previews.attackrange then
        for _, u in units do
            local bp = u:GetBlueprint()
            if bp.Weapon ~= nil then
                for _wIndex, w in bp.Weapon do
                    local radius = w.MaxRadius;
                    if not ACSdata.rings.attackrange[radius] then
                        local texture = getTextureForWeapon(w)
                        if texture ~= nil then 
                            createRing(ACSdata.rings.attackrange,texture, radius, 0, 0, 0, 0)
                        end
                    end
                end
            end
        end
    end
    ACSdata.isPreviewAlive = true
end

function getTextureForWeapon(weapon)
    if weapon.RangeCategory == "UWRC_DirectFire" then
        return acs_modpath..'textures/direct_ring.dds'
    elseif weapon.RangeCategory == "UWRC_IndirectFire" then
        return acs_modpath..'textures/indirect_ring.dds'
    end
    return nil -- dont display AA, torp, etc
end

function createRing(group, texture, radius, x1, x2, y1, y2)
    if not group[radius] then
        local ring = Decal(GetFrame(0))
        ring:SetTexture(texture)
        ring:SetScale({math.floor(2.03*(radius + x1) + x2), 0, math.floor(2.03*(radius + y1)) + y2})
        ring:SetPosition(GetMouseWorldPos())
        group[radius] = ring
    end
end


function createPreviewOfCurrentSelection()
    createRangeRingPreviews(GetSelectedUnits() or {})
end

function updatePreview()
    if (not ACSdata.isPreviewAlive) then
        createPreviewOfCurrentSelection()
    end
    for _, group in ACSdata.rings do
        for __, ring in group do
            ring:SetPosition(GetMouseWorldPos())
        end
    end
end

function removePreview()
    if (not ACSdata.isPreviewAlive) then
        return
    end
    for n, group in ACSdata.rings do
        for n2, ring in group do
            ring:Destroy()
            ACSdata.rings[n][n2] = nil
        end
    end
    ACSdata.isPreviewAlive = false
end


local oldWorldView = WorldView 
WorldView = Class(oldWorldView, Control) {

    isZoom = true,
    isPreviewBuildrange = false,
    isPreviewAttackrange = false,
    previewKey = "SHIFT",

    HandleEvent = function(self, event)
        if (not self.isZoom) and (event.Type == 'WheelRotation') then
            return true
        end
        return oldWorldView.HandleEvent(self, event)
    end,

    OnUpdateCursor = function(self)
        if (self.isPreviewBuildrange or self.isPreviewAttackrange) then
            if IsKeyDown(self.previewKey) and (isAcceptablePreviewMode(CM.GetCommandMode())) then
                updatePreview()
            else
                removePreview()
            end
        end
        return oldWorldView.OnUpdateCursor(self)
    end,

    SetAllowZoom = function(self, bool)
        self.isZoom = bool
    end,

    SetPreviewBuildrange = function(self, bool)
        self.isPreviewBuildrange = bool
        ACSdata.previews.buildrange = bool
        removePreview()
    end,

    SetPreviewAttackrange = function(self, bool)
        self.isPreviewAttackrange = bool
        ACSdata.previews.attackrange = bool
        removePreview()
    end,

    SetPreviewKey = function(self, newKey)
        self.previewKey = newKey
    end,
}
