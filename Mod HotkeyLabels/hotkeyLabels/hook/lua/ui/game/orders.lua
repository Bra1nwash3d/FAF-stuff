local hotkeyLabel_modpath = "/mods/hotkeyLabels/"
local hotkeyLabel_addLabel = import(hotkeyLabel_modpath..'modules/hotkeylabelsUI.lua').addLabel

local orderKeys = {}


function setOrderKeys(orderKeys_)
    orderKeys = orderKeys_
end


local oldAddOrder = AddOrder
function AddOrder(orderInfo, slot, batchMode)
    local retval = oldAddOrder(orderInfo, slot, batchMode)
    if orderKeys[orderInfo.helpText] then
        hotkeyLabel_addLabel(retval, retval, orderKeys[orderInfo.helpText])
    end
    return retval
end