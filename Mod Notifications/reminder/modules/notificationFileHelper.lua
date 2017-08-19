--[[
	notificationType: SCRIPT, TIMED, CONDITIONALTIMED
]]

local modpath = "/mods/reminder"
local notificationPrefs = import(modpath..'/modules/notificationPrefs.lua')

local prefs = notificationPrefs.getPreferences()


function getNotificationsInDir(dir, notificationType)
	filesInDir = {}
	for i, file in DiskFindFiles(dir, "*") do
		LOG('Notification Mod: loading... '..file)
		table.insert(filesInDir, file)
	end
	return loadNotificationsInList(filesInDir, notificationType)
end


function loadNotificationsInList(list, notificationType)
	local allNotificationsInList = {}
	local prefs = notificationPrefs.getPreferences()
	
	for _,cur in list do		
		allNotificationsInList[cur] = {}
		allNotificationsInList[cur].id = cur
		allNotificationsInList[cur].blockedTimer = 0

		-- unknown notification?
		-- default notification options
		if prefs.notification[cur].states == nil then
			allNotificationsInList[cur].states = {}
			for _, defaultPref in notificationPrefs.getDefaultNotificationPrefs() do
				allNotificationsInList[cur].states[defaultPref.path] = defaultPref.defaultValue
			end
			notificationPrefs.setNotificationState(cur, allNotificationsInList[cur].states)
		else
			for id,_ in prefs.notification[cur] do
				allNotificationsInList[cur][id] = prefs.notification[cur][id]
			end
		end

		-- settings for this notification
		if prefs.notification[cur].preferences == nil then
			allNotificationsInList[cur].preferences = {}
		end
		for _, preferenceTable in import(cur).getDefaultConfig() or {} do
			if not allNotificationsInList[cur].preferences[preferenceTable.path] then
				allNotificationsInList[cur].preferences[preferenceTable.path] = preferenceTable.value
			end
		end
		notificationPrefs.setNotificationPreferences(cur, allNotificationsInList[cur].preferences)

		if notificationType == "TIMED" or notificationType == "CONDITIONALTIMED" then
			allNotificationsInList[cur].nextTrigger = allNotificationsInList[cur].preferences["triggerAtSeconds"]
		end
	end
	return allNotificationsInList
end


function getTexture(resourceName, path, isModFile)
	if isModFile then
		return path..resourceName
	end
	
	for _, file in DiskFindFiles('/textures/', resourceName) do
		return file
	end	
end


function getSound(resource, isModFile)
	if isModFile then
		return nil --not supported yet
	end
	
	return resource
end



