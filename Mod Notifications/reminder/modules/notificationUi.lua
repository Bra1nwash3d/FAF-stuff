local modpath = '/mods/reminder/'
local notificationPrefs = import(modpath..'modules/notificationPrefs.lua')
local notificationUtils = import(modpath..'modules/notificationUtils.lua')
local notificationSizes = import(modpath..'modules/notificationUiSizes.lua')

local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local UIUtil = import('/lua/ui/uiutil.lua')
local Group = import('/lua/maui/group.lua').Group
local Button = import('/lua/maui/button.lua').Button
local Bitmap = import('/lua/maui/bitmap.lua').Bitmap
local Dragger = import('/lua/maui/dragger.lua').Dragger

local Tooltip = import('/lua/ui/game/tooltip.lua')


local REMOVE_CLICKBITMAP_AFTER_SECONDS = 20

local savedPrefs = nil
local notificationMainSizes = nil
local notificationPanelSizes = nil
local isVisible = nil
local isNotificationsToPositiveX = nil
local mainPanel = nil

local notifications = {}

local buttons = {
	dragButton = nil,
	hideButton = nil,
	configButton = nil
}
local defaultButtonTextures = {
	dragButton = nil,
}

local tooltips = {
	_delay = 0.2,
	drag = {
		text = "Drag",
		body = "Keep the button pressed and move the cursor around",
	},
	minimize = {
		text = "Quick minimize",
		body = "Quickly hide/show the notifications",
	},
	config = {
		text = "Configuration",
		body = "Configure everything to your liking",
	},
}


function init()
	-- settings
	savedPrefs = notificationPrefs.getPreferences()
	notificationMainSizes = notificationSizes.getNotificationMainSizes()
	notificationPanelSizes = notificationSizes.getNotificationPanelSizes()
	
	isNotificationsToPositiveX = savedPrefs.global.isNotificationsToPositiveX
	isVisible = savedPrefs.global.isVisible
	
	mainPanel = Bitmap(GetFrame(0))
	mainPanel.Depth:Set(99)
	LayoutHelpers.AtLeftTopIn(mainPanel, GetFrame(0), savedPrefs.global.xOffset, savedPrefs.global.yOffset)
	mainPanel.Height:Set(notificationMainSizes.buttonSize)
	mainPanel.Width:Set(notificationMainSizes.buttonSize)
	
	addMainpanelButtons()

	notificationPrefs.addPreferenceChangeListener(function()
		savedPrefs = notificationPrefs.getPreferences()
		
		setIsVisible(savedPrefs.global.isVisible)
		isNotificationsToPositiveX = savedPrefs.global.isNotificationsToPositiveX
		resetPosY()
		
		if(savedPrefs.global.isButtonsSetLeft) then
			moveMainpanelButtons("left")
		else
			moveMainpanelButtons("right")
		end

		setMainButtonTextures()
	end)
end


-----------------------------------------------------------------------


function addMainpanelButtons()
	local dragButtonUpTexture = modpath..'textures/drag_up.dds'
	if savedPrefs.global.isButtonsOnlyOnMouseover == true then
		dragButtonUpTexture = modpath..'textures/transparent.png'
	end

	-- initializing them transparent, they will change once the main function inits
	buttons.dragButton = Button(mainPanel, modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png')
	buttons.dragButton.Height:Set(notificationMainSizes.buttonSize)
	buttons.dragButton.Width:Set(notificationMainSizes.buttonSize)
	LayoutHelpers.AtLeftTopIn(buttons.dragButton, mainPanel, notificationMainSizes.buttonXOffset, 0)
	
	buttons.hideButton = Button(mainPanel, modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png')
	buttons.hideButton.Height:Set(notificationMainSizes.buttonSize)
	buttons.hideButton.Width:Set(notificationMainSizes.buttonSize)
	Tooltip.AddButtonTooltip(buttons.hideButton, tooltips.minimize, tooltips._delay)
	LayoutHelpers.AtLeftTopIn(buttons.hideButton, mainPanel, notificationMainSizes.buttonXOffset + (notificationMainSizes.buttonSize+notificationMainSizes.buttonDistance)*1, 0)
	
	buttons.configButton = Button(mainPanel, modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png')
	buttons.configButton.Height:Set(notificationMainSizes.buttonSize)
	buttons.configButton.Width:Set(notificationMainSizes.buttonSize)
	Tooltip.AddButtonTooltip(buttons.configButton, tooltips.config, tooltips._delay)
	LayoutHelpers.AtLeftTopIn(buttons.configButton, mainPanel, notificationMainSizes.buttonXOffset + (notificationMainSizes.buttonSize+notificationMainSizes.buttonDistance)*2, 0)
	
	buttons.dragButton.HandleEvent = function(self, event)
		if (event.Type == "MouseEnter") then
			Tooltip.CreateMouseoverDisplay(self, tooltips.drag, tooltips._delay, true)
		elseif event.Type == 'MouseExit' then
			Tooltip.DestroyMouseoverDisplay()
		end

		if event.Type == 'ButtonPress' then
			self:SetTexture(modpath..'textures/drag_down.dds')

			if not savedPrefs.global.isDraggable then
				return
			end

			local drag = Dragger()
			local offX = event.MouseX - self.Left()
			local offY = event.MouseY - self.Top()
			drag.OnMove = function(dragself, x, y)
				mainPanel.Left:Set(x - offX + (mainPanel.Left() - buttons.dragButton.Left()))
				mainPanel.Top:Set(y - offY)
				GetCursor():SetTexture(UIUtil.GetCursor('MOVE_WINDOW'))
			end
			drag.OnRelease = function(dragself)
				notificationPrefs.setXYvalues(self.Left(), self.Top())
				GetCursor():Reset()
				drag:Destroy()
			end
			PostDragger(self:GetRootFrame(), event.KeyCode, drag)
		
		elseif event.Type == 'MouseMotion' or event.Type == 'MouseEnter' then
			self:SetTexture(modpath..'textures/drag_over.dds')
		else
			self:SetTexture(defaultButtonTextures.dragButton)
		end
	end
	
	buttons.hideButton:EnableHitTest(true)
	buttons.hideButton.OnClick = function(self, event)
		if not savedPrefs.global.isMinimizable then
			return
		end
		if(isVisible == true) then
			setIsVisible(false)
		else
			setIsVisible(true)
		end
		notificationPrefs.setIsVisible(isVisible)
	end
	
	buttons.configButton:EnableHitTest(true)
	buttons.configButton.OnClick = function(self, event)
		import(modpath..'modules/notificationPrefsUi.lua').createPrefsUi()
	end
	
	if not ( savedPrefs.global.isButtonsSetLeft ) then
		moveMainpanelButtons("right")
	end
end


function setMainButtonTextures()
	defaultButtonTextures.dragButton = modpath..'textures/drag_up.dds'
	local hideButtonUpTexture = modpath..'textures/hide_up.dds'
	local configButtonUpTexture = modpath..'textures/options_up.dds'
	if savedPrefs.global.isButtonsOnlyOnMouseover == true then
		defaultButtonTextures.dragButton = modpath..'textures/transparent.png'
		hideButtonUpTexture = modpath..'textures/transparent.png'
		configButtonUpTexture = modpath..'textures/transparent.png'
	end

	buttons.dragButton:SetTexture(defaultButtonTextures.dragButton)
	buttons.dragButton:SetNewTextures(
		defaultButtonTextures.dragButton,
		modpath..'textures/drag_down.dds',
		modpath..'textures/drag_over.dds',
		modpath..'textures/drag_up.dds')

	buttons.hideButton:SetTexture(hideButtonUpTexture)
	buttons.hideButton:SetNewTextures(
		hideButtonUpTexture,
		modpath..'textures/hide_down.dds',
		modpath..'textures/hide_over.dds',
		modpath..'textures/hide_up.dds')

	buttons.configButton:SetTexture(configButtonUpTexture)
	buttons.configButton:SetNewTextures(
		configButtonUpTexture,
		modpath..'textures/options_down.dds',
		modpath..'textures/options_over.dds',
		modpath..'textures/options_up.dds')
end


function moveMainpanelButtons(s)
	helpDistance = notificationMainSizes.buttonSize + notificationMainSizes.buttonDistance
	helpOffsetX = 0
	
	if s == "right" then
		helpOffsetX = notificationPanelSizes.width - 3*helpDistance + notificationMainSizes.buttonDistance
	end
	
	LayoutHelpers.AtLeftTopIn(buttons.dragButton, mainPanel, helpOffsetX + helpDistance*0, 0)
	LayoutHelpers.AtLeftTopIn(buttons.hideButton, mainPanel, helpOffsetX + helpDistance*1, 0)
	LayoutHelpers.AtLeftTopIn(buttons.configButton, mainPanel, helpOffsetX + helpDistance*2, 0)
end


function setIsVisible(bool)
	if ( isVisible == bool ) then
		return
	end
	isVisible = bool
	showNotifications(bool)
end


function setNotificationsTowardsPositiveX(bool)
	if ( isNotificationsToPositiveX == bool ) then
		return
	end
	isNotificationsToPositiveX = bool
end


-----------------------------------------------------------------------


function createNotification(data, insertAt)
	posY = nil
	if isNotificationsToPositiveX then
		posY  = notificationUtils.countTableElements(notifications) * (notificationMainSizes.distance + notificationPanelSizes.height) + (notificationMainSizes.buttonSize + notificationMainSizes.distance)
	else
		posY  = (notificationUtils.countTableElements(notifications)+1) * (notificationMainSizes.distance + notificationPanelSizes.height) * (-1)
	end
	
	if(notifications[data.id].clickButton) then
		notifications[data.id].clickButton:Destroy()
	end
	notifications[insertAt] = getNotificationUI(data.text, data.subtext, data.icons, data.clickFunctionLeft, data.clickFunctionRight, posY)
end


function getNotificationUI(text, subtext, icons, clickFunctionLeft, clickFunctionRight, posY)
	notificationPanel = {}
	
	-- notification body
	notificationPanel.main = Bitmap(mainPanel)
	notificationPanel.main.Depth:Set(99)
	LayoutHelpers.AtLeftTopIn(notificationPanel.main, mainPanel, 0, posY)
	notificationPanel.main.Height:Set(notificationPanelSizes.height)
	notificationPanel.main.Width:Set(notificationPanelSizes.width)	
	notificationPanel.main:DisableHitTest(true)
	notificationPanel.main:SetTexture('/textures/ui/common/game/economic-overlay/econ_bmp_m.dds')
	
	-- icons
	smallerBy = notificationPanelSizes.height - notificationPanelSizes.iconHeight
	notificationPanel.iconPanels = {}
	for i, icon in icons do
		local iconPanel = Bitmap(mainPanel)
		iconPanel.Height:Set(notificationPanelSizes.iconHeight)
		iconPanel.Width:Set(notificationPanelSizes.iconHeight)
		iconPanel:DisableHitTest(true)
		iconPanel:SetTexture(icons[i])
		LayoutHelpers.AtLeftTopIn(iconPanel, notificationPanel.main, smallerBy/2, smallerBy/2)
		notificationPanel.iconPanels[i] = iconPanel
	end
	
	-- text
	notificationPanel.text = UIUtil.CreateText(notificationPanel.main, text, notificationPanelSizes.textSize, UIUtil.bodyFont)
	notificationPanel.subtext = UIUtil.CreateText(notificationPanel.main, subtext, notificationPanelSizes.subtextSize, UIUtil.bodyFont)
	LayoutHelpers.AtLeftTopIn(notificationPanel.text, notificationPanel.main, notificationPanelSizes.height+10, notificationPanelSizes.textYIn)
	LayoutHelpers.AtLeftTopIn(notificationPanel.subtext, notificationPanel.main, notificationPanelSizes.height+10, notificationPanelSizes.subtextYIn)
	notificationPanel.text:DisableHitTest(true)
	notificationPanel.subtext:DisableHitTest(true)
	
	-- click function button
	notificationPanel.clickButton = Button(mainPanel, modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png', modpath..'textures/transparent.png')
	LayoutHelpers.AtLeftTopIn(notificationPanel.clickButton, notificationPanel.main, 0, 0)
	notificationPanel.clickButton.Height:Set(notificationPanelSizes.height)
	notificationPanel.clickButton.Width:Set(notificationPanelSizes.width)
	
	notificationPanel.clickButton.OnClick = function(self, event)
		if(savedPrefs.global.isClickEvent and notificationPanel.clickButton) then
			if event.Left and clickFunctionLeft then
				clickFunctionLeft()
			end			
			if event.Right and clickFunctionRight then
				clickFunctionRight()
			end			
		end
	end
	
	showNotification(notificationPanel, isVisible)
	return notificationPanel
end


function removeNotification(id)
	if notifications[id] == nil then
		return
	end
	
	notifications[id].clickButton.Height:Set(0)
	notifications[id].clickButton.Width:Set(0)
	
	notifications[id].main:Destroy()
	for _, iconPanel in notifications[id].iconPanels do
		iconPanel:Destroy()
	end

	local clickPanelToRemove = notifications[id].clickButton
	ForkThread(function()
		WaitSeconds(REMOVE_CLICKBITMAP_AFTER_SECONDS)
		clickPanelToRemove:Destroy()
	end)

	notifications[id].iconPanels = nil
	notifications[id] = nil

	resetPosY()
end


function resetPosY()
	local posY = notificationMainSizes.buttonSize + notificationMainSizes.distance
	local add = notificationMainSizes.distance + notificationPanelSizes.height
	if not isNotificationsToPositiveX then
		posY = 0 - notificationMainSizes.distance - notificationPanelSizes.height
		add = add * (-1)
	end
	
	for _,panel in notifications do
		LayoutHelpers.AtLeftTopIn(panel.main, mainPanel, 0, posY)
		posY = posY + add
	end
end


function showNotifications(isVisible)
	for _,notification in notifications do
		showNotification(notification, isVisible)
	end
end


function showNotification(notificationPanel, isVisible)
	if(isVisible == false) then
		notificationPanel.main:Hide()
		for _, iconPanel in notificationPanel.iconPanels do
			iconPanel:Hide()
		end
		notificationPanel.clickButton:Hide()
	else
		notificationPanel.main:Show()
		for _, iconPanel in notificationPanel.iconPanels do
			iconPanel:Show()
		end
		notificationPanel.clickButton:Show()
	end	
end