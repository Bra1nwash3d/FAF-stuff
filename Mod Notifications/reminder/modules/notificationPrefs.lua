local Prefs = import('/lua/user/prefs.lua')
local savedPrefs = Prefs.GetFromCurrentProfile("reminder_settings")

local preferenceChangeListener = {}


function init()
	-- create defaults
	if not savedPrefs then
		savedPrefs = {}
	end
	
	if not savedPrefs.global then
		savedPrefs.global = {
			xOffset = 2,
			yOffset = 156,
			startDelay = 60,
			duration = 5,
			minRetriggerDelay = 15,
			isVisible = true,
			isMinimizable = true,
			isDraggable = true,
			isButtonsSetLeft = true,
			isNotificationsToPositiveX = true,
			isPlaySound = false,
			isClickEvent = true,
			uiSize = 2,
			isButtonsOnlyOnMouseover = false,
			isPing = false,
		}
	end
	
	if savedPrefs.notification == nil then
		savedPrefs.notification = {}
	end
	
	-- correct x/y if outside the window
	if (savedPrefs.global.xOffset < 0 or savedPrefs.global.xOffset > GetFrame(0).Width()
			or savedPrefs.global.yOffset < 0 or savedPrefs.global.yOffset > GetFrame(0).Height()) then
		savedPrefs.global.xOffset = GetFrame(0).Width()/2
		savedPrefs.global.yOffset = GetFrame(0).Height()/2
	end
	
	-- add new stuff --
	-- 2.5
	if not savedPrefs.global.uiSize then
		savedPrefs.global.uiSize = 2
	end
	-- 4.0
	if not savedPrefs.global.isButtonsOnlyOnMouseover then
		savedPrefs.global.isButtonsOnlyOnMouseover = false
	end
	if not savedPrefs.global.isPing then
		savedPrefs.global.isPing = false
	end
	
	-- removing old stuff --
	-- <2.0
	savedPrefs.notificationIsActive = nil
	savedPrefs.xOffset = nil
	savedPrefs.yOffset = nil
	savedPrefs.isVisible = nil
	
	savePreferences()
end


function addPreferenceChangeListener(listener)
	table.insert(preferenceChangeListener, listener)
end


function removeNotificationsNotInTables(list)
	for id,value in savedPrefs.notification do
		local isInList = false
		for _, l in list do
			if isInTable(id, l) then
				isInList = true
				break
			end
		end
		if not isInList then
			LOG('Notification Mod: [\''..id..'\'] is not found anymore, is removed from game.prefs')
			savedPrefs.notification[id] = nil
		end
	end
	savePreferences()
end


function isInTable(id, t)
	for id2,_ in t do
		if(id == id2) then
			return true
		end
	end
	return false
end


function savePreferences()
	Prefs.SetToCurrentProfile("reminder_settings", savedPrefs)
	Prefs.SavePreferences()
	for _, listener in preferenceChangeListener do
		listener()
	end
end


---------


function getPreferences()
	return savedPrefs
end


function setIsVisible(bool)
	savedPrefs.global.isVisible = bool
	savePreferences()
end


function setXYvalues(posX, posY)
	savedPrefs.global.xOffset = posX
	savedPrefs.global.yOffset = posY
	savePreferences()
end


function setNotificationState(configId, t)
	setNotificationSubtable(configId, "states", t)
end


function setNotificationPreferences(configId, t)
	setNotificationSubtable(configId, "preferences", t)
end


function setNotificationSubtable(configId, subtable, t)
	if not savedPrefs.notification[configId] then
		savedPrefs.notification[configId] = {}
	end
	if not savedPrefs.notification[configId][subtable] then
		savedPrefs.notification[configId][subtable] = {}
	end
	for id, value in t or {} do
		savedPrefs.notification[configId][subtable][id] = value
	end
	savePreferences()
end


function saveModifiedPrefs(newSavedPrefs)
	savedPrefs = newSavedPrefs
	savePreferences()
end



----------------------------------------------------------------------

function getDefaultNotificationPrefs()
	return {
		[1] = {
			name = "Notification is active",
			path = "isActive",
			defaultValue = true
		},
		[2] = {
			name = "Notification displays text",
			path = "isDisplay",
			defaultValue = true
		},
		[3] = {
			name = "Notification can play sounds",
			path = "isPlaySound",
			defaultValue = false
		},
		[4] = {
			name = "Notification pings related units",
			path = "isPing",
			defaultValue = false
		}
	}
end