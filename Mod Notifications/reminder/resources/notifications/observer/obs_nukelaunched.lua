local modpath = "/mods/reminder"
local observerLayer = import(modpath.."/modules/notificationObserverLayer.lua")


function getDefaultConfig()
	return 	{}
end
local runtimeConfig = {
	text = "Nuke launched",
	subtext = "Strategic launch detected",
	icons = {{icon='abstract/nuke/nuke.png', isModFile=true}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end

local registeredLaunch = false

function init()
	observerLayer.addUserSyncFunction(function(syncTable)
		for k, v in syncTable.Voice do
			if v.Bank == "XGG" and v.Cue == "Computer_Computer_MissileLaunch_01351" then
				registeredLaunch = true
			end
		end
	end)
end


function triggerNotification()
	if registeredLaunch then
		registeredLaunch = false
		return true
	end
	return false
end


function onUpdatePreferences(savedConfig)
end