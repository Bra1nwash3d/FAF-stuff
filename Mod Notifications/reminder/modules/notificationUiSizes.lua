local modpath = '/mods/reminder/'
local notificationPrefs = import(modpath..'modules/notificationPrefs.lua')

local size = notificationPrefs.getPreferences().global.uiSize

local notificationMainSizes = {
	[1] = {
		distance = 4,
		buttonSize = 16,
		buttonDistance = 2,
		buttonXOffset = 0
	},
	[2] = {
		distance = 4,
		buttonSize = 18,
		buttonDistance = 2,
		buttonXOffset = 0
	},
	[3] = {
		distance = 4,
		buttonSize = 20,
		buttonDistance = 3,
		buttonXOffset = 0
	},
}
	
	
local notificationPanelSizes = {
	[1] = {
		height = 45,
		width = 240,
		textSize = 16,
		textYIn = 6,
		subtextSize = 12,
		subtextYIn = 25,
		iconHeight = 43,
	},
	[2] = {
		height = 60,
		width = 300,
		textSize = 22,
		textYIn = 8,
		subtextSize = 14,
		subtextYIn = 34,
		iconHeight = 58,
	},
	[3] = {
		height = 70,
		width = 360,
		textSize = 28,
		textYIn = 8,
		subtextSize = 18,
		subtextYIn = 40,
		iconHeight = 68,
	},
}
	
	
local notificationPrefsSizes = {
	[1] = {
		height = 0,
		width = 600,
		additionalHeightTop = 50,
		additionalHeightOptions = 240,
		additionalHeightNotifications = 55,
		additionalHeightBottom = 35,
		headlineYIn = 30,
		options = {
			height = 14,
			distance = 4
		},
		textSize = {
			headline = 20,
			section = 16,
			option = 12,
		},
	},
	[2] = {
		height = 0,
		width = 600,
		additionalHeightTop = 50,
		additionalHeightOptions = 250,
		additionalHeightNotifications = 60,
		additionalHeightBottom = 40,
		headlineYIn = 34,
		options = {
			height = 17,
			distance = 4
		},
		textSize = {
			headline = 22,
			section = 18,
			option = 14,
		},
	},
	[3] = {
		height = 0,
		width = 800,
		additionalHeightTop = 80,
		additionalHeightOptions = 340,
		additionalHeightNotifications = 65,
		additionalHeightBottom = 50,
		headlineYIn = 40,
		options = {
			height = 20,
			distance = 6
		},
		textSize = {
			headline = 28,
			section = 22,
			option = 16,
		},
	},
}

	
function getNotificationMainSizes()
	return notificationMainSizes[size] or notificationMainSizes[1]
end

function getNotificationPanelSizes()
	return notificationPanelSizes[size] or notificationPanelSizes[1]
end

function getNotificationPrefsSizes()
	return notificationPrefsSizes[size] or notificationPrefsSizes[1]
end

function getMaxSize()
	return table.getn(notificationPrefsSizes)
end
