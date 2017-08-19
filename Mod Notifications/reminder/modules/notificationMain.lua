local ping = import('/lua/ui/game/ping.lua')

local modpath = "/mods/reminder/"
local iconpath = modpath.."resources/icons/"
local soundpath = modpath.."resources/sounds/"

-- paths to different notification kinds
local notificationScripts = modpath.."resources/notifications/scripts/"
local notificationTimed = modpath.."resources/notifications/timed/"
local notificationConditionalTimed = modpath.."resources/notifications/conditionalTimed/"
local notificationObserver = modpath.."resources/notifications/observer/"

local ui = import(modpath..'modules/notificationUi.lua')
local notificationFileHelper = import(modpath..'modules/notificationFileHelper.lua')

local notificationPrefs = import(modpath..'modules/notificationPrefs.lua')
local savedPrefs = notificationPrefs.getPreferences()

-- lists of different notification kinds
local allNotifications = {
	script = nil,
	timed = nil,
	condintionalTimed = nil,
	observer = nil,
}
local cachedNotificationImports = {}

local currentlyActiveNotifications = {}
local insertAt = 1
local currentCycleIndex = 1


function init()
	WaitSeconds(1)
	
	loadNotifications()
	cacheNotificationImports()
	savedPrefs = notificationPrefs.getPreferences()
	onPreferencesChanged()
	notificationPrefs.addPreferenceChangeListener(import(modpath..'modules/notificationMain.lua').onPreferencesChanged)
	
	WaitSeconds(savedPrefs.global.startDelay -1)

	-- init script notifications
	for _,n in allNotifications.script do
		cachedNotificationImports[n.id].init()
	end
	-- init observer notifications
	for _,n in allNotifications.observer do
		cachedNotificationImports[n.id].init()
	end
	
	triggerNotificationChecks()
end


function loadNotifications()
	allNotifications.script = notificationFileHelper.getNotificationsInDir(notificationScripts, "SCRIPT")
	allNotifications.timed = notificationFileHelper.getNotificationsInDir(notificationTimed, "TIMED")
	allNotifications.condintionalTimed = notificationFileHelper.getNotificationsInDir(notificationConditionalTimed, "CONDITIONALTIMED")
	allNotifications.observer = notificationFileHelper.getNotificationsInDir(notificationObserver, "OBSERVER")
	notificationPrefs.removeNotificationsNotInTables({allNotifications.script, allNotifications.timed, allNotifications.condintionalTimed, allNotifications.observer})
end


function cacheNotificationImports()
	for _, group in allNotifications do
		for _, n in group do
			cachedNotificationImports[n.id] = import(n.id)
		end
	end
end


-- looping through all known notifications and checking if it should trigger them
function triggerNotificationChecks()
	while(true) do
		WaitSeconds(0.1)
		local globalRetriggerDelay = savedPrefs.global.minRetriggerDelay
		
		-- script notifications
		for _,n in allNotifications.script do
			if( savedPrefs.notification[n.id].states.isActive ) then
				n.blockedTimer = n.blockedTimer - 0.1
				if(n.blockedTimer < 0) then
					if(cachedNotificationImports[n.id].triggerNotification()) then
						handleNotification(n)
						n.blockedTimer = globalRetriggerDelay
					end
				else
					cachedNotificationImports[n.id].onRetriggerDelay()
				end
			end
		end
		
		-- observer notifications
		-- these do not get a retrigger delay, but to group them up, only check each half second
		for _,n in allNotifications.observer do
			if( savedPrefs.notification[n.id].states.isActive ) then
				n.blockedTimer = n.blockedTimer - 0.1
				if(n.blockedTimer < 0) then
					if(cachedNotificationImports[n.id].triggerNotification()) then
						handleNotification(n)
					end
					n.blockedTimer = 0.5
				end
			end
		end

		gameTime = GetGameTimeSeconds()

		-- timed notifications
		for i,n in allNotifications.timed do
			if( savedPrefs.notification[n.id].states.isActive ) then
				if(n.nextTrigger < gameTime) then
					handleNotification(n)
					if (savedPrefs.notification[n.id].preferences.canRetrigger == true) then
						n.nextTrigger = gameTime + math.max(globalRetriggerDelay, savedPrefs.notification[n.id].preferences.retriggerDelay)
					else
						allNotifications.timed[i] = nil
					end
				end
			end
		end
		
		-- conditional timed notifications
		for i,n in allNotifications.condintionalTimed do
			if( savedPrefs.notification[n.id].states.isActive ) then
				n.blockedTimer = n.blockedTimer - 0.1
				if(n.nextTrigger < gameTime and n.blockedTimer < 0) then
					if(cachedNotificationImports[n.id].triggerNotification()) then
						handleNotification(n)
						if (savedPrefs.notification[n.id].preferences.canRetrigger == true) then
							n.nextTrigger = gameTime + math.max(globalRetriggerDelay, savedPrefs.notification[n.id].preferences.retriggerDelay)
						else
							allNotifications.condintionalTimed[i] = nil
						end
					else
						allNotifications.condintionalTimed[i] = nil
					end
				end
			end
		end
	end
end


function handleNotification(notification)
	-- visual
	if (savedPrefs.notification[notification.id].states.isDisplay == true) then
		ForkThread(createAndDeleteNotificationUi, notification, insertAt)
		insertAt = insertAt+1
	end

	local runtimeConfig = cachedNotificationImports[notification.id].getRuntimeConfig()

	-- sound
	-- requires a runtimeConfig.sound = {sound = pathToFile, isModFile=false} styled input
	if( savedPrefs.global.isPlaySound and savedPrefs.notification[notification.id].states.isPlaySound == true ) then
		local sound = runtimeConfig.sound
		if not ((sound == false) or (sound == nil)) then
			PlaySound(notificationFileHelper.getSound(sound.sound, sound.isModFile))
		end
	end

	-- ping
	if( savedPrefs.global.isPing and savedPrefs.notification[notification.id].states.isPing == true ) then
		createPing(runtimeConfig.unitsToSelect)
	end
end


function createAndDeleteNotificationUi(notification, position)
	local notificationConfig = cachedNotificationImports[notification.id].getRuntimeConfig()
	notification.text = notificationConfig.text
	notification.subtext = notificationConfig.subtext

	local unitsToSelect = table.deepcopy(notificationConfig.unitsToSelect, {})

	notification.clickFunctionLeft = function()
		if unitsToSelect == nil then
			return false
		end
		if table.getn(unitsToSelect) < 1 then
			return false
		end
		SelectUnits(unitsToSelect)
		return true
	end
	notification.clickFunctionRight = function()
		if unitsToSelect == nil then
			return false
		end
		if table.getn(unitsToSelect) < 1 then
			return false
		end
		SelectUnits(unitsToSelect)
		UIZoomTo(unitsToSelect)
		return true
	end
	
	notification.icons = {}
	for i, v in notificationConfig.icons do
		notification.icons[i] = notificationFileHelper.getTexture(notificationConfig.icons[i].icon, iconpath, notificationConfig.icons[i].isModFile)
	end

	ui.createNotification(notification, position)
	currentlyActiveNotifications[position] = notification
	
	WaitSeconds(savedPrefs.global.duration)
	
	ui.removeNotification(position)
	currentlyActiveNotifications[position] = nil
end


function createPing(units)
	if (units == nil) then
		return
	end
	if (table.getn(units) < 1) then
		return
	end

	local hasPing = false
	local data = {}

	for _, u in units do
		if (not u:IsDead()) then
			hasPing = true
			table.insert(data, {
				Type = "alert_marker",
				Owner = (GetArmiesTable().focusArmy - 1),
				Sound = '', --'UEF_Select_Radar',
				Lifetime = 6,
				Location = u:GetPosition(),
				Mesh = 'alert_marker',
				Ring = '/game/marker/ring_yellow02-blur.dds',
				ArrowColor = 'yellow',
			})
		end
	end

	if hasPing then
		ping.DisplayPing(data)
	end
end


----------------------------------------------------------------------------------------------------
-- preferences changed

function onPreferencesChanged()
	savedPrefs = notificationPrefs.getPreferences()
	-- update notifications
	for _, group in allNotifications do
		for _,n in group do
			cachedNotificationImports[n.id].onUpdatePreferences(savedPrefs.notification[n.id].preferences)
		end
	end
end


----------------------------------------------------------------------------------------------------
-- keeping track of currently displayed notifications

function getFirstNotificationId()
	local firstId = nil
	for id, _ in currentlyActiveNotifications do
		if id < firstId or firstId == nil then
			firstId = id
		end
	end
	return firstId
end
function getFirstNotification()
	return currentlyActiveNotifications[getFirstNotificationId()]
end

function getLastNotificationId()
	local lastId = nil
	for id, _ in currentlyActiveNotifications do
		if id > lastId  or lastId == nil then
			lastId = id
		end
	end
	return lastId
end
function getLastNotification()
	local id = getLastNotificationId()
	if id then
		return currentlyActiveNotifications[id]
	end
	return nil
end

----------------------------------------
-- cycling of displayed notifications

function leftclickLast()
	currentCycleIndex = getLastNotificationId()
	cycleNotificationsLeftclick()
end
function rightclickLast()
	currentCycleIndex = getLastNotificationId()
	cycleNotificationsRightclick()
end


function cycleNotificationsLeftclick()
	cycleNotifications("Left")
end
function cycleNotificationsRightclick()
	cycleNotifications("Right")
end

function cycleNotifications(leftRight)
	local first = getFirstNotificationId()
	local last = getLastNotificationId()
	if first == nil or last == nil then
		return
	end
	currentCycleIndex = triggerNextNotification(currentCycleIndex, first, last, leftRight, last-first)
end

function triggerNextNotification(cur, first, last, leftRight, triesLeft)
	if triesLeft < 0 then
		return cur
	end
	
	if cur < first then
		cur = last
	end
	
	local clickFunction = currentlyActiveNotifications[cur].clickFunctionRight
	if leftRight == "Left" then
		clickFunction = currentlyActiveNotifications[cur].clickFunctionLeft
	end
	
	if clickFunction() then
		return cur-1
	end
	return triggerNextNotification(cur-1, first, last, leftRight, triesLeft-1)
end
