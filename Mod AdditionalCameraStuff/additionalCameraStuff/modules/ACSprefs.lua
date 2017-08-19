local modpath = "/mods/additionalCameraStuff/"
local utils = import(modpath..'modules/ACSutils.lua')

local Prefs = import('/lua/user/prefs.lua')
local ASCprefsName = "ACS_settings"
local savedPrefs = nil

local preferenceChangeListener = {}


local defaults = {
    { name = "Camera", settings = {
        { key="isSavePositionAtHeight", type="bool", default=false, name="Save positions at fixed height", description="The hotkeys to save camera positions use a fixed height" },
        { key="savePositionsAtHeight", type="number", default=20, name="Save position height", description="At which height the positions will ", min=100, max=500, valMult=1, execute = import(modpath..'modules/ACScamera.lua').onSettingsSliderChanges },
    }},
    { name = "Minimap", settings = {
        { key="isZoomEnabled", type="bool", default=true, name="Zoom is enabled", description="Allow scrolling on the minimap to zoom it" },
        { key="isResizableAndDraggable", type="bool", default=true, name="Dragging, resizing and resetbutton are enabled", description="Disabling will block resizing or moving the minimap and hide the reset button" },
        { key="isClosable", type="bool", default=true, name="Closing the window is enabled", description="Disabling will block the close button" },
    }},
    { name = "Other", settings = {
        { key="isPreviewBuildrange", type="bool", default=false, name="Preview buildrange (shift)", description="Shows the buildranges as if the selected units were located at the cursor position" },
        { key="isPreviewAttackrange", type="bool", default=false, name="Preview attackrange (shift)", description="Shows the attackranges as if the selected units were located at the cursor position" },
        { key="isPreviewKeyCtrl", type="bool", default=false, name="Previews use ctrl instead of shift", description="" },
    }},
}


function init()
    local tooltips = import('/lua/ui/help/tooltips.lua').Tooltips
    savedPrefs = Prefs.GetFromCurrentProfile(ASCprefsName)

    -- create defaults
    if not savedPrefs then
        savedPrefs = {}
    end

    for _, group in defaults do
        if not savedPrefs[group.name] then
            savedPrefs[group.name] = {}
        end
        for __, setting in group.settings do
            -- defaults
            if (savedPrefs[group.name][setting.key] == nil) then
                savedPrefs[group.name][setting.key] = setting.default
            end

            tooltips["ACS_"..setting.key] = {
                title = setting.name,
                description = setting.description,
                keyID = "ACS_"..setting.key,
            }
        end
    end

    -- TODO: delete unused settings
    savePreferences()

    -- had typo before, removing prefs saved in the wrong path
    Prefs.SetToCurrentProfile("ASC_settings", nil)
end


function getFullSettings()
    return defaults
end


function addPreferenceChangeListener(listener)
    table.insert(preferenceChangeListener, listener)
end


function savePreferences()
    Prefs.SetToCurrentProfile(ASCprefsName, savedPrefs)
    Prefs.SavePreferences()
    for _, listener in preferenceChangeListener do
        listener()
    end
end


function getPreferences()
    return savedPrefs
end


function saveModifiedPrefs(newSavedPrefs)
    savedPrefs = newSavedPrefs
    savePreferences()
end