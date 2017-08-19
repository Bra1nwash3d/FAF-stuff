local modpath = "/mods/additionalCameraStuff/"
local prefs = nil

local positionChangeObserver = {}
local cameraPositions = {}

local prevPositions = {}
local insertAt = 1
local size = 2
local cur = 1

local isUseFixedCameraHeight = false
local fixedCameraHeight = 0


function init()
    prefs = import(modpath..'modules/ACSprefs.lua')
    isUseFixedCameraHeight = prefs.getPreferences().Camera.isSavePositionAtHeight
    fixedCameraHeight = prefs.getPreferences().Camera.savePositionsAtHeight

    prefs.addPreferenceChangeListener(function()
        local savedPrefs = prefs.getPreferences()
        isUseFixedCameraHeight = prefs.getPreferences().Camera.isSavePositionAtHeight
        fixedCameraHeight = prefs.getPreferences().Camera.savePositionsAtHeight
    end)
end

-- triggered by hotkey
function setCameraPosition(i)
    cameraPositions[i] = GetCamera('WorldCamera'):SaveSettings()
    if isUseFixedCameraHeight then
        cameraPositions[i].Zoom = fixedCameraHeight
    end
    onPositionsChange()
end

-- triggered by hotkey
function restoreCameraPosition(i)
    if not cameraPositions[i] then
        return
    end
    addPrevPosition(GetCamera('WorldCamera'):SaveSettings())
    GetCamera('WorldCamera'):RestoreSettings(cameraPositions[i])
end

-- triggered by hotkey
function jumpToPrevPosition()
    local index = getPrevIndex()
    if index == nil then
        return
    end
    cur = index
    GetCamera('WorldCamera'):RestoreSettings(prevPositions[index])
end


function addPrevPosition(pos)
    prevPositions[insertAt] = pos

    insertAt = insertAt+1
    if insertAt > size then
        insertAt = 1
    end
    cur = insertAt
end


function getPrevIndex()
    local help
    for i=1, size+1 do
        help = cur-i
        if help < 1 then
            help = help + size
        end
        if prevPositions[help] then
            return help
        end
    end
    return nil
end


function addPositionChangeObserver(f)
    table.insert(positionChangeObserver, f)
end


function onPositionsChange()
    for i, f in positionChangeObserver do
        f(cameraPositions)
    end
end


function onSettingsSliderChanges(value)
    GetCamera('WorldCamera'):SetZoom(value, 0) 
end