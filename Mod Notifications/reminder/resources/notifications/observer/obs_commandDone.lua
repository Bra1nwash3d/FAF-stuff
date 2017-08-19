local modpath = "/mods/reminder"
local observerLayer = import(modpath.."/modules/notificationObserverLayer.lua")


function getDefaultConfig()
	return 	{}
end
local runtimeConfig = {
	text = "Command executed",
	subtext = "",
	icons = {},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end


local checkedUnits = {}


function init()
	checkedUnits = {}

	local KeyMapper = import('/lua/keymap/keymapper.lua')
	KeyMapper.SetUserKeyAction('Notifications: Add command finished notification', {action = "UI_Lua import('"..modpath.."/resources/notifications/observer/obs_commandDone.lua').onAddCommand()", category = 'Mods', order = 1020,})

	observerLayer.addCommandIssuedFunction(function(command)
		if command.CommandType == "None" then
			return
		end

		if command.Clear or command.CommandType == "Stop" then
			for _, u in command.Units do
				checkedUnits[u:GetEntityId()] = nil
			end
		else
			for _, u in command.Units do
				if checkedUnits[u:GetEntityId()] then
					for _, l in checkedUnits[u:GetEntityId()].checkedList do
						l.followedTasks = l.followedTasks + 1
					end
				end
			end
		end
	end)
end


function triggerNotification()
	runtimeConfig.unitsToSelect = {}

	-- checking for dead units
	local deadUnits = 0
	for id, u in checkedUnits do
		if u.unit:IsDead() then
			runtimeConfig.icons[2] = {
				icon= u.icon,
				isModFile=false
			}

			checkedUnits[id] = nil
			deadUnits = deadUnits + 1
		end
	end

	if deadUnits > 0 then
		if deadUnits > 1 then
			runtimeConfig.text = deadUnits.."units died"
			runtimeConfig.subtext = "before completing their order"
		else
			runtimeConfig.text = "One unit died"
			runtimeConfig.subtext = "before completing its order"
		end
		runtimeConfig.icons[3] = {icon='abstract/attacked.png', isModFile=true}
		return true
	end

	-- checking for units which completed their task
	for id, u in checkedUnits do
		local amount = table.getn(u.unit:GetCommandQueue())
		for i, l in u.checkedList do
			l.tasksLeft = amount - l.followedTasks

			if l.tasksLeft <= 0 then
				u.checkedList[i] = nil
				table.insert(runtimeConfig.unitsToSelect, u.unit)
			end
		end

		local ordersLeft = 0
		for _, __ in u.checkedList do
			ordersLeft = ordersLeft + 1
		end
		if ordersLeft < 1 then
			checkedUnits[id] = nil
		end
	end

	local numSelected = table.getn(runtimeConfig.unitsToSelect)
	if numSelected > 0 then
		runtimeConfig.text = "Command executed"
		if numSelected > 1 then
			runtimeConfig.subtext = numSelected.." units executed their order"
		else
			runtimeConfig.subtext = "One unit executed its order"
		end

		local unitToPick = runtimeConfig.unitsToSelect[1]
		runtimeConfig.icons[2] = {
			icon= runtimeConfig.unitsToSelect[1]:GetBlueprint().BlueprintId..'_icon.dds',
			isModFile=false
		}
		runtimeConfig.icons[3] = nil
		return true
	end

	return false
end


----------------------------------------------


function onAddCommand()
	local curUnits = GetSelectedUnits() or {}
	for _, u in curUnits do
		if not checkedUnits[u:GetEntityId()] then
			checkedUnits[u:GetEntityId()] = {
				unit = u,
				icon = u:GetBlueprint().BlueprintId..'_icon.dds',
				checkedList = {}
			}
		end
		table.insert(checkedUnits[u:GetEntityId()].checkedList, {
			tasksLeft = table.getn(u:GetCommandQueue()),
			followedTasks = 0,
		})
	end
end


function onUpdatePreferences(savedConfig)
end