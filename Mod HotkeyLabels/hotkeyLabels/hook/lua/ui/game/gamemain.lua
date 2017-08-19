local modpath = "/mods/hotkeyLabels/"
local hotkeyLabelsInit = import(modpath..'modules/hotkeyLabels.lua').init
local hotkeyLabelsOnSelectionChanged = import(modpath..'modules/hotkeyLabels.lua').onSelectionChanged

local originalCreateUI = CreateUI
function CreateUI(isReplay) 
    originalCreateUI(isReplay)
    hotkeyLabelsInit()
end


local originalOnSelectionChanged = OnSelectionChanged
function OnSelectionChanged(oldSelection, newSelection, added, removed)
    if table.getn(newSelection) > 0 then
        local upgradesTo = newSelection[1]:GetBlueprint().General.UpgradesTo
        if upgradesTo then
            if upgradesTo:len(upgradesTo) < 7 then
                upgradesTo = nil
            end
        end
        local isFactory = newSelection[1]:IsInCategory("FACTORY")
        hotkeyLabelsOnSelectionChanged(upgradesTo, isFactory)
    end

    return originalOnSelectionChanged(oldSelection, newSelection, added, removed)
end