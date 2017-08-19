local hotkeyLabel_modpath = "/mods/hotkeyLabels/"
local hotkeyLabel_addLabel = import(hotkeyLabel_modpath..'modules/hotkeylabelsUI.lua').addLabel

local idRelations = {}
local upgradeKey = nil
local upgradesTo = nil
local allowOthers = true


function setIdRelations(idRelations_, upgradeKey_)
    idRelations = idRelations_
    upgradeKey = upgradeKey_
end


function setUpgradeAndAllowing(upgradesTo_, allowOthers_)
    upgradesTo = upgradesTo_
    allowOthers = allowOthers_
end


local oldCommonLogic = CommonLogic
function CommonLogic()
    local retval = oldCommonLogic()
    local key = nil
    local id = nil
    
    local oldControl = controls.choices.SetControlToType
    controls.choices.SetControlToType = function(control, type)
        oldControl(control, type)
        id = control.Data.id
        if type == 'item' then
            if id == upgradesTo and upgradeKey then
                hotkeyLabel_addLabel(control, control.Icon, upgradeKey)
            elseif allowOthers or (upgradesTo == nil) then
                key = idRelations[id]
                if key then
                    hotkeyLabel_addLabel(control, control.Icon, key)
                end
            end
        end
    end

    return retval
end