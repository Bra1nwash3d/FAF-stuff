local modpath = "/mods/additionalCameraStuff/"
local prefs = import(modpath..'modules/ACSprefs.lua')
local main = import(modpath..'modules/ACSmain.lua')
local worldView = import("/lua/ui/game/worldview.lua")

local amountOfCameraPoints = 5
local orderCategory = "Mod: Additional Camera Stuff"


function init()
    initPrefs()
    initCamera()
    initUI()
    initOther()
    prefs.saveModifiedPrefs(prefs.getPreferences())
end


function initPrefs()
    prefs.init()
end


function initCamera()
    import(modpath..'modules/ACScamera.lua').init()
    local KeyMapper = import('/lua/keymap/keymapper.lua')

    KeyMapper.SetUserKeyAction("Jump to previous camera position", {action = "UI_Lua import('"..modpath.."modules/ACScamera.lua').jumpToPrevPosition()", category = orderCategory, order = 100,})

    for i = 1, amountOfCameraPoints do
        KeyMapper.SetUserKeyAction('Set camera position '..i, {action = "UI_Lua import('"..modpath.."modules/ACScamera.lua').setCameraPosition("..i..")", category = orderCategory, order = 100+2*i,})
        KeyMapper.SetUserKeyAction('Go to camera position '..i, {action = "UI_Lua import('"..modpath.."modules/ACScamera.lua').restoreCameraPosition("..i..")", category = orderCategory, order = 101+2*i,})
    end
end


function initUI()
    import(modpath..'modules/ACSUI.lua').init(import('/lua/ui/game/borders.lua').GetMapGroup(false), amountOfCameraPoints)
end


function initOther()
    worldView.addViewChangeListener(function()
        main.updateWorldviews()
    end)

    prefs.addPreferenceChangeListener(function()
        main.updateWorldviews()
    end)
end


function updateWorldviews()
    local savedPrefs = prefs.getPreferences()
    for _, view in {worldView.viewLeft, worldView.viewRight} do
        if view then
            view:SetPreviewBuildrange(savedPrefs.Other.isPreviewBuildrange)
            view:SetPreviewAttackrange(savedPrefs.Other.isPreviewAttackrange)
            view:SetPreviewKey("SHIFT")
            if savedPrefs.Other.isPreviewKeyCtrl then
                view:SetPreviewKey("CONTROL")
            end
        end
    end
end