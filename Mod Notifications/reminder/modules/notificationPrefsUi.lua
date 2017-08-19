local modpath = '/mods/reminder/'
local utils = import(modpath..'modules/notificationUtils.lua')
local notificationUi = import(modpath..'modules/notificationUi.lua')
local notificationSizes = import(modpath..'modules/notificationUiSizes.lua')

local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local UIUtil = import('/lua/ui/uiutil.lua')
local Button = import('/lua/maui/button.lua').Button
local Bitmap = import('/lua/maui/bitmap.lua').Bitmap
local Checkbox = import('/lua/maui/checkbox.lua').Checkbox
local IntegerSlider = import('/lua/maui/slider.lua').IntegerSlider

local notificationPrefs = import(modpath..'modules/notificationPrefs.lua')
local uiPanelSettings = notificationSizes.getNotificationPrefsSizes()

local savedPrefs = nil
local curPrefs = nil

local uiPanel = {
	main = nil,
	globalPreferences = nil,
	notifications = nil,
	singleNotificationSetting = nil,
}



function createPrefsUi()
	if uiPanel.singleNotificationSetting then
		uiPanel.singleNotificationSetting:Destroy()
		uiPanel.singleNotificationSetting = nil
	end
	if uiPanel.main then
		uiPanel.main:Destroy()
		uiPanel.main = nil
		return
	end

	-- copy configs to local, to not mess with the original ones until they should save
	savedPrefs = notificationPrefs.getPreferences()
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
	curY = curY + uiPanelSettings.additionalHeightTop + 15
	
	-- global prefs
	setGlobalPrefs(uiPanel.main, 0, curY-25, uiPanelSettings.width, uiPanelSettings.additionalHeightOptions)
	curY = curY + uiPanelSettings.additionalHeightOptions
	
	-- notifications
	setNotificationList(uiPanel.main, 0, curY, uiPanelSettings.width, uiPanelSettings.height - uiPanelSettings.additionalHeightTop - uiPanelSettings.additionalHeightOptions - uiPanelSettings.additionalHeightBottom)

	--buttons
	local okButtonFunction = function()
		notificationPrefs.saveModifiedPrefs(curPrefs)
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
	uiPanelSettings.height = (utils.countTableElements(savedPrefs.notification)/2) * (uiPanelSettings.options.height + uiPanelSettings.options.distance)+ uiPanelSettings.options.distance + uiPanelSettings.additionalHeightBottom + uiPanelSettings.additionalHeightTop + uiPanelSettings.additionalHeightOptions  + uiPanelSettings.additionalHeightNotifications
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


function setGlobalPrefs(parent, posX, posY, width, height)
	uiPanel.globalPreferences = Bitmap(parent)
	uiPanel.globalPreferences.Depth:Set(99)
	LayoutHelpers.AtLeftTopIn(uiPanel.globalPreferences, uiPanel.main, posX, posY)
	uiPanel.globalPreferences.Height:Set(height)
	uiPanel.globalPreferences.Width:Set(width)
	uiPanel.globalPreferences:SetTexture(modpath..'textures/transparent.png')
	uiPanel.globalPreferences:Show()

	LayoutHelpers.CenteredAbove(UIUtil.CreateText(uiPanel.globalPreferences, "Global", uiPanelSettings.textSize.section, UIUtil.bodyFont), uiPanel.globalPreferences, -25)
	createOptions(uiPanel.globalPreferences, 35)
end


function createOptions(parent, posY)	
	---- left side options
	local curY = posY
	local curX = 0
	
	-- isDraggable
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "main buttons can be dragged", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isDraggable"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
	
	-- isButtonsOnlyOnMouseover
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "main buttons hidden until cursor is over", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isButtonsOnlyOnMouseover"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
	
	--
	curY = curY + (uiPanelSettings.options.height + uiPanelSettings.options.distance)/2	

	-- isMinimizable
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "allow quick minimizing", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isMinimizable"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
	
	-- isButtonsSetLeft
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "main buttons located on left side", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isButtonsSetLeft"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance	
	
	-- isNotificationsToPositiveX
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "notifications located below main buttons", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isNotificationsToPositiveX"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance	

	--
	curY = curY + (uiPanelSettings.options.height + uiPanelSettings.options.distance)/2

	-- isVisible
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "notifications are visible", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isVisible"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
	
	-- isClickEvent
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "allow click events", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isClickEvent"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance	

	-- isPlaySound
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "allow sounds", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isPlaySound"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance	
	
	-- isPing
	LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(parent, "allow pings", uiPanelSettings.textSize.option, UIUtil.bodyFont), parent, curX+30, curY)
	createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"global", "isPing"})
	curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance	
	
	---- right side options
	curY = posY
	curX = uiPanelSettings.width / 2
	
	createSettingsSliderWithText(parent, curPrefs, curX, curY, "notification duration: ", uiPanelSettings.width/2, 1, 20, 1, {"global", "duration"})
	curY = curY + 2.5*(uiPanelSettings.options.height + uiPanelSettings.options.distance)
	
	createSettingsSliderWithText(parent, curPrefs, curX, curY, "min retrigger delay: ", uiPanelSettings.width/2, 1, 24, 5, {"global", "minRetriggerDelay"})
	curY = curY + 2.5*(uiPanelSettings.options.height + uiPanelSettings.options.distance)
	
	createSettingsSliderWithText(parent, curPrefs, curX, curY, "mod startup time (next game): ", uiPanelSettings.width/2, 1, 20, 30, {"global", "startDelay"})
	curY = curY + 2.5*(uiPanelSettings.options.height + uiPanelSettings.options.distance)
	
	createSettingsSliderWithText(parent, curPrefs, curX, curY, "UI size (next game): ", uiPanelSettings.width/2, 1, notificationSizes.getMaxSize(), 1, {"global", "uiSize"})
	curY = curY + 2.5*(uiPanelSettings.options.height + uiPanelSettings.options.distance)
end


function setNotificationList(parent, posX, posY, width, height)
	uiPanel.notifications = Bitmap(parent)
	uiPanel.notifications.Depth:Set(99)
	LayoutHelpers.AtLeftTopIn(uiPanel.notifications, uiPanel.main, posX, posY)
	uiPanel.notifications.Height:Set(height)
	uiPanel.notifications.Width:Set(width)
	uiPanel.notifications:SetTexture(modpath..'textures/transparent.png')
	uiPanel.notifications:Show()

	LayoutHelpers.CenteredAbove(UIUtil.CreateText(uiPanel.notifications, "Notifications", uiPanelSettings.textSize.section, UIUtil.bodyFont), uiPanel.notifications, -25)
	createNotificationList(uiPanel.notifications, 35)
end


function createNotificationList(parent, posY)
	count = 0
	local curX = 0
	local curY = posY

	for id, value in curPrefs.notification do
		local curId = id

		local notificationText = UIUtil.CreateText(parent, utils.getFilenameWithoutDir(id), uiPanelSettings.textSize.option, UIUtil.bodyFont)
		notificationText:DisableHitTest(true)
		LayoutHelpers.AtLeftTopIn(notificationText, parent, curX+30, curY)
		createSettingCheckbox(parent, curPrefs, curX+10, curY+2, 13, {"notification", curId, "states", "isActive"})

		local notificationPrefsButton = Button(parent, modpath..'textures/transparent.png', modpath..'textures/transparent_with_edges.png', modpath..'textures/transparent_with_edges.png', modpath..'textures/transparent_with_edges.png')
		LayoutHelpers.AtLeftTopIn(notificationPrefsButton, parent, curX+25, curY)
		notificationPrefsButton.Height:Set(uiPanelSettings.options.height)
		notificationPrefsButton.Width:Set((uiPanelSettings.width / 2) - 25)
		notificationPrefsButton.OnClick = function(self)
			createSingleNotificationPrefs(curId, {"notification", curId, "preferences"})
		end

		if(utils.modulo(count, 2) == 0) then
			curX = uiPanelSettings.width / 2
		else
			curX = 0
			curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
		end
		count = count+1
	end
end


---------------------------------------------------------------------


function createSingleNotificationPrefs(id, settingsPath)
	if uiPanel.singleNotificationSetting then
		uiPanel.singleNotificationSetting:Destroy()
		uiPanel.singleNotificationSetting = nil
		return
	end
	uiPanel.main:Hide()

	-- prefs copy
	local localPrefs = table.deepcopy(curPrefs.notification[id], {})
	local notificationFile = import(id)

	-- panel
	createNotificatoinPrefsUi()
	local curX = 0
	local curY = 0
	
	LayoutHelpers.CenteredAbove(UIUtil.CreateText(uiPanel.singleNotificationSetting, utils.getFilenameWithoutDir(id), uiPanelSettings.textSize.headline, UIUtil.bodyFont), uiPanel.singleNotificationSetting, -curY-uiPanelSettings.headlineYIn)
	
	curY = curY + uiPanelSettings.additionalHeightTop + 15
	
	LayoutHelpers.CenteredAbove(UIUtil.CreateText(uiPanel.singleNotificationSetting, "Preferences", uiPanelSettings.textSize.section, UIUtil.bodyFont), uiPanel.singleNotificationSetting, -curY)
	curY = curY + 15
	
	-- prefs in "states", default for all
	for _, defaultPref in notificationPrefs.getDefaultNotificationPrefs() do
		LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(uiPanel.singleNotificationSetting, defaultPref.name, uiPanelSettings.textSize.option, UIUtil.bodyFont), uiPanel.singleNotificationSetting, curX+30, curY)
		createSettingCheckbox(uiPanel.singleNotificationSetting, localPrefs, curX+10, curY+2, 13, {"states", defaultPref.path})
		curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
	end
	curY = curY + 2*(uiPanelSettings.options.height + uiPanelSettings.options.distance)

	-- prefs in "config", each notification its own settings
	for _, singlePref in notificationFile.getDefaultConfig() or {} do
		-- is it a slider option?
		if not (singlePref.slider == nil) then
			createSettingsSliderWithText(uiPanel.singleNotificationSetting, localPrefs, curX, curY, singlePref.name, uiPanelSettings.width, singlePref.slider.minVal, singlePref.slider.maxVal, singlePref.slider.valMult, {"preferences", singlePref.path})
			curY = curY + 2.5*(uiPanelSettings.options.height + uiPanelSettings.options.distance)

		-- or a checkbox option?
		else
			LayoutHelpers.AtLeftTopIn(UIUtil.CreateText(uiPanel.singleNotificationSetting, singlePref.name, uiPanelSettings.textSize.option, UIUtil.bodyFont), uiPanel.singleNotificationSetting, curX+30, curY)
			createSettingCheckbox(uiPanel.singleNotificationSetting, localPrefs, curX+10, curY+2, 13, {"preferences", singlePref.path})
			curY = curY + uiPanelSettings.options.height + uiPanelSettings.options.distance
		end
	end

	local okButtonFunction = function()
		curPrefs.notification[id] = localPrefs
		uiPanel.singleNotificationSetting:Destroy()
		uiPanel.singleNotificationSetting = nil
		rebuildPrefsUi()
	end
	local cancelButtonFunction = function()
		uiPanel.singleNotificationSetting:Destroy()
		uiPanel.singleNotificationSetting = nil
		uiPanel.main:Show()
	end
	createOkCancelButtons(uiPanel.singleNotificationSetting, okButtonFunction, cancelButtonFunction)

end


function createNotificatoinPrefsUi()
	posX = GetFrame(0).Width()/2 - uiPanelSettings.width/2
	posY = GetFrame(0).Height()/2 - uiPanelSettings.height/2
	
	uiPanel.singleNotificationSetting = Bitmap(GetFrame(0))
	uiPanel.singleNotificationSetting.Depth:Set(99)
	LayoutHelpers.AtLeftTopIn(uiPanel.singleNotificationSetting, GetFrame(0), posX, posY)
	uiPanel.singleNotificationSetting.Height:Set(uiPanelSettings.height)
	uiPanel.singleNotificationSetting.Width:Set(uiPanelSettings.width)
	uiPanel.singleNotificationSetting:SetTexture('/textures/ui/common/game/economic-overlay/econ_bmp_m.dds')
	uiPanel.singleNotificationSetting:Show()
end


---------------------------------------------------------------------


function createSettingCheckbox(parent, prefs, posX, posY, size, args)
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
end


function createSettingsSliderWithText(parent, prefs, posX, posY, text, size, minVal, maxVal, valMult, args)
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
		valueText:SetText(newValue*valMult)
		setCurPrefByArgs(prefs, args, newValue*valMult)
	end
	
    slider._background.Width:Set(size-20)
	slider.Width:Set(size-20)
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