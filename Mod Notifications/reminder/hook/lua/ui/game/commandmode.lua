local reminder_observerLayer = import("/mods/reminder/modules/notificationObserverLayer.lua")
local oldOnCommandIssued = OnCommandIssued

function OnCommandIssued(command)
	oldOnCommandIssued(command)
	ForkThread(reminder_observerLayer.onOnCommandIssued, command)
end