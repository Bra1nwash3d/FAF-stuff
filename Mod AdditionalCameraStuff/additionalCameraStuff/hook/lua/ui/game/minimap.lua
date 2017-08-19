local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local Button = import('/lua/maui/button.lua').Button
local Tooltip = import('/lua/ui/game/tooltip.lua')
local Prefs = import('/lua/user/prefs.lua')

local acs_modpath = "/mods/additionalCameraStuff/"
local prefs = import(acs_modpath..'modules/ACSprefs.lua')
local prefsUI = import(acs_modpath..'modules/ACSprefsUI.lua')

local isMinimapZoom = false
local isResetButtonEnabled = true
local isCloseButtonEnabled = true

local oldCreateMinimap = CreateMinimap
function CreateMinimap(parent)
    oldCreateMinimap(parent)
    controls.miniMap:SetAllowZoom(isMinimapZoom)

    controls.displayGroup.prefsButton = Button(controls.displayGroup.TitleGroup,
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_up.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_down.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_over.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_dis.dds'))
    LayoutHelpers.LeftOf(controls.displayGroup.prefsButton, controls.displayGroup.resetBtn)

    controls.displayGroup.prefsButton.OnClick = function(self)
        prefsUI.createPrefsUi()
    end

    Tooltip.AddButtonTooltip(controls.displayGroup.prefsButton, {
        text = "ACS Preferences",
        body = "Opens the Additional Camera Stuff preferences",
    })

    local oldResetButtonFunction = controls.displayGroup.resetBtn.OnClick
    controls.displayGroup.resetBtn.OnClick = function(modifiers)
        if isResetButtonEnabled then
            oldResetButtonFunction(modifiers)
        end
    end

    local oldCloseButtonFunction = controls.displayGroup.OnClose
    controls.displayGroup.OnClose = function(self)
        if isCloseButtonEnabled then
            oldCloseButtonFunction(self)
        end
    end

    prefs.addPreferenceChangeListener(function()
        local savedPrefs = prefs.getPreferences()
        controls.miniMap:SetAllowZoom(savedPrefs.Minimap.isZoomEnabled)
        controls.displayGroup._lockSize = (not savedPrefs.Minimap.isResizableAndDraggable)
        controls.displayGroup._lockPosition = (not savedPrefs.Minimap.isResizableAndDraggable)
        isResetButtonEnabled = savedPrefs.Minimap.isResizableAndDraggable
        isCloseButtonEnabled = savedPrefs.Minimap.isClosable
    end)
end