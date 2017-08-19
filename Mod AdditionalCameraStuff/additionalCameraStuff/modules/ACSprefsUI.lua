local modpath = "/mods/additionalCameraStuff/"

local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local UIUtil = import('/lua/ui/uiutil.lua')
local Button = import('/lua/maui/button.lua').Button
local Bitmap = import('/lua/maui/bitmap.lua').Bitmap
local Checkbox = import('/lua/maui/checkbox.lua').Checkbox
local IntegerSlider = import('/lua/maui/slider.lua').IntegerSlider
local Tooltip = import('/lua/ui/game/tooltip.lua')

local ACSprefs = import(modpath..'modules/ACSprefs.lua')
local uiPanelSettings = {
    height = 500,
    width = 400,
    textSize = {
        headline = 20,
        group = 17,
        option = 14,
    },
    options = {
        height = 30,
        distance = 2,
    },
    headlineYIn = 30,
    additionalHeightBottom = 40,
}

local savedPrefs = nil
local curPrefs = nil

local uiPanel = {
    main = nil,
    singleNotificationSetting = nil,
}



function createPrefsUi()
    if uiPanel.main then
        uiPanel.main:Destroy()
        uiPanel.main = nil
        return
    end

    -- copy configs to local, to not mess with the original ones until they should save
    savedPrefs = ACSprefs.getPreferences()
    curPrefs = table.deepcopy(savedPrefs, {})

    rebuildPrefsUi()
end


function rebuildPrefsUi()
    -- create the ui
    if uiPanel.main then
        uiPanel.main:Destroy()
        uiPanel.main = nil
    end
    createMainPanel()
    curY = 0
    
    LayoutHelpers.CenteredAbove(UIUtil.CreateText(uiPanel.main, "Preferences", uiPanelSettings.textSize.headline, UIUtil.bodyFont), uiPanel.main, -curY-uiPanelSettings.headlineYIn)
    curY = curY + 30

    createOptions(uiPanel.main, curY)

    --buttons
    local okButtonFunction = function()
        ACSprefs.saveModifiedPrefs(curPrefs)
        uiPanel.main:Destroy()
        uiPanel.main = nil
    end
    local cancelButtonFunction = function()
        uiPanel.main:Destroy()
        uiPanel.main = nil
    end
    createOkCancelButtons(uiPanel.main, okButtonFunction, cancelButtonFunction)
end


---------------------------------------------------------------------


function createMainPanel()
    posX = GetFrame(0).Width()/2 - uiPanelSettings.width/2
    posY = GetFrame(0).Height()/2 - uiPanelSettings.height/2
    
    uiPanel.main = Bitmap(GetFrame(0))
    uiPanel.main.Depth:Set(99)
    LayoutHelpers.AtLeftTopIn(uiPanel.main, GetFrame(0), posX, posY)
    uiPanel.main.Height:Set(uiPanelSettings.height)
    uiPanel.main.Width:Set(uiPanelSettings.width)
    uiPanel.main:SetTexture('/textures/ui/common/game/economic-overlay/econ_bmp_m.dds')
    uiPanel.main:Show()
end


function createOptions(parent, posY)
    local settingGroups = ACSprefs.getFullSettings()
    local curX = 30
    local curY = posY + 10

    for _, group in settingGroups do
        if group.name ~= "Hidden" then
            curY = curY + 10
            LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(uiPanel.main, group.name, uiPanelSettings.textSize.group, UIUtil.bodyFont), uiPanel.main, curX-20, curY)
            curY = curY + 30

            for __, setting in group.settings do
                if setting.type == "bool" then
                    createSettingCheckbox(uiPanel.main, curPrefs, curX, curY, 13, {group.name, setting.key}, setting.name, setting.key)
                    curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
                elseif setting.type == "number" then
                    createSettingsSliderWithText(uiPanel.main, curPrefs, curX, curY, setting.name, uiPanel.main.Width() * 0.9, setting.min, setting.max, setting.valMult, {group.name, setting.key}, setting)
                    curY = curY + 2.5* (uiPanelSettings.options.height + uiPanelSettings.options.distance)
                else
                    LOG("Unknown settings type: " .. setting.type)
                end
            end
        end
    end
end


---------------------------------------------------------------------


function createSettingCheckbox(parent, prefs, posX, posY, size, args, settingName, settingKey)
    local value = prefs
    local argsCopy = args

    for _,v in args do
        value = value[v]
    end

    local box = UIUtil.CreateCheckbox(parent, '/CHECKBOX/')
    box.Height:Set(size)
    box.Width:Set(size)
    if (value == true) or (value > 0) then
        box:SetCheck(true, true)
    else
        box:SetCheck(false, true)
    end
    
    box.OnClick = function(self)
        if(box:IsChecked()) then
            setCurPrefByArgs(prefs, argsCopy, false)
            value = false
            box:SetCheck(false, true)
        else
            setCurPrefByArgs(prefs, argsCopy, true)
            value = true
            box:SetCheck(true, true)
        end
    end
    LayoutHelpers.AtLeftTopIn(box, parent, posX, posY+1)

    LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, settingName, uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, posX + 20, posY)
    Tooltip.AddCheckboxTooltip(box, 'ACS_' .. settingKey)
end


function createSettingsSliderWithText(parent, prefs, posX, posY, text, size, minVal, maxVal, valMult, args, setting)
    -- name
    LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, text, uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, posX+10, posY)
    
    -- value
    local value = prefs
    for _, v in args do
        value = value[v]
    end
    if value < minVal*valMult then
        value = minVal*valMult
    elseif value > maxVal*valMult then
        value = maxVal*valMult
    end
    
    -- value text
    local valueText = UIUtil.CreateText(parent, value, uiPanelSettings.textSize.option, UIUtil.bodyFont)
    LayoutHelpers.AtLeftTopIn(valueText, parent, posX+(size*9/10), posY)
    
    local slider = IntegerSlider(parent, false, minVal,maxVal, 1, UIUtil.SkinnableFile('/slider02/slider_btn_up.dds'), UIUtil.SkinnableFile('/slider02/slider_btn_over.dds'), UIUtil.SkinnableFile('/slider02/slider_btn_down.dds'), UIUtil.SkinnableFile('/slider02/slider-back_bmp.dds'))  
    LayoutHelpers.AtLeftTopIn(slider, parent, posX+10, posY + uiPanelSettings.options.height + uiPanelSettings.options.distance)
    slider:SetValue(value/valMult)

    slider.OnValueChanged = function(self, newValue)
        if setting.execute then
            setting.execute(newValue)
        end
        valueText:SetText(newValue*valMult)
        setCurPrefByArgs(prefs, args, newValue*valMult)
    end
    
    slider._background.Width:Set(size-20)
    slider.Width:Set(size-20)
    Tooltip.AddCheckboxTooltip(slider, 'ACS_' .. setting.key)
end


function createOkCancelButtons(parent, okButtonFunction, cancelButtonFunction)
    okCancelButtonHeight = uiPanelSettings.additionalHeightBottom-15
    
    local okButton = Button(parent, modpath.."/textures/checked_up.png", modpath.."/textures/checked_down.png", modpath.."/textures/checked_over.png", modpath.."/textures/checked_up.png")
    LayoutHelpers.AtLeftTopIn(okButton, parent, uiPanelSettings.width-2*okCancelButtonHeight-15, uiPanelSettings.height-okCancelButtonHeight-10)
    okButton.Height:Set(okCancelButtonHeight)
    okButton.Width:Set(okCancelButtonHeight)
    okButton.OnClick = function(self)
        if not (okButtonFunction == nil) then
            okButtonFunction()
        end
    end
    
    local cancelButton = Button(parent, modpath.."/textures/unchecked_up.png", modpath.."/textures/unchecked_down.png", modpath.."/textures/unchecked_over.png", modpath.."/textures/unchecked_up.png")
    LayoutHelpers.AtLeftTopIn(cancelButton, parent, uiPanelSettings.width-okCancelButtonHeight-5, uiPanelSettings.height-okCancelButtonHeight-10)
    cancelButton.Height:Set(okCancelButtonHeight)
    cancelButton.Width:Set(okCancelButtonHeight)
    cancelButton.OnClick = function(self)
        if not (cancelButtonFunction == nil) then
            cancelButtonFunction()
        end
    end
end


function setCurPrefByArgs(prefs, args, value)   
    num = table.getn(args)
    if num==2 then
        prefs[args[1]][args[2]] = value
    end
    if num==4 then
        prefs[args[1]][args[2]][args[3]][args[4]] = value
    end
end