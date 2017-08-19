local observerLayer = import("/mods/reminder/modules/notificationObserverLayer.lua")
local oldOnSync = OnSync

function OnSync()
	oldOnSync()
	ForkThread(observerLayer.onUserSync, Sync)
end
