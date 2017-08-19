local modpath = "/mods/reminder"
local utils = import(modpath..'/modules/notificationUtils.lua')
local units = import('/mods/common/units.lua')

local worldCamera = import('/lua/ui/game/worldview.lua').GetWorldViews()["WorldCamera"]; 
local UserDecal = import('/lua/user/UserDecal.lua').UserDecal


local savedConfig = nil
local unitData = {
	smds = {
		category = categories.ANTIMISSILE * categories.TECH3 * categories.STRUCTURE,
		texts = {
			text = "Nuke Defense Lost!",
			subtext1 = "Lost ",
			subtext2 = " nuke defense!",
		},
		icon = nil,
		savedUnits = {},
		isActive = true,
	},
	omnis = {
		category = categories.OMNI * categories.TECH3,
		texts = {
			text = "Omni Sensor Lost!",
			subtext1 = "Lost ",
			subtext2 = " omni sensor!",
		},
		icon = nil,
		savedUnits = {},
		isActive = true,
	},
}


function getDefaultConfig()
	return {
		[1] = {
			name = "Mark position of lost units",
			path = "useMarker",
			value = true,
		},
		[2] = {
			name = "For how long the marker is displayed",
			value = 20,
			path = "markerDuration",
			slider = {
				minVal = 5,
				maxVal = 60,
				valMult = 1,
			}
		},
		[3] = {
			name = "Check nuke defense",
			path = "checkSMD",
			value = true,
		},
		[4] = {
			name = "Check omni sensor",
			path = "checkOmni",
			value = true,
		},
	}
end
local runtimeConfig = {
	text = "",
	subtext = "",
	icons = {[1] = {icon='land_up.dds', isModFile=false}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end


function init()
	local faction = utils.getFaction()
	if faction == "UEF" then
		unitData.omnis.icon = {icon='UEB3104_icon.dds', isModFile=false}
		unitData.smds.icon = {icon='UEB4302_icon.dds', isModFile=false}
	elseif faction == "AEON" then
		unitData.omnis.icon = {icon='UAB3104_icon.dds', isModFile=false}
		unitData.smds.icon = {icon='UAB4302_icon.dds', isModFile=false}
	elseif faction == "CYBRAN" then
		unitData.omnis.icon = {icon='URB3104_icon.dds', isModFile=false}
		unitData.smds.icon = {icon='URB4302_icon.dds', isModFile=false}
	else
		unitData.omnis.icon = {icon='XSB3104_icon.dds', isModFile=false}
		unitData.smds.icon = {icon='xsb4302_icon.dds', isModFile=false}
	end
end


function triggerNotification()
	local lost = 0

	-- check lost ones
	for _, group in unitData do
		if group.isActive then
			for id, t in group.savedUnits do
				if t.unit:IsDead() then
					lost = lost + 1
					group.savedUnits[id] = nil
					if savedConfig.useMarker then
						markPosition(t.pos)
					end
				end
			end
			if lost > 0 then
				runtimeConfig.text = group.texts.text
				runtimeConfig.subtext = group.texts.subtext1..lost..group.texts.subtext2
				runtimeConfig.icons[2] = group.icon
				return true
			end
		end
	end

	-- get units
	addUnits()
	return false
end


function onRetriggerDelay()
	addUnits()
end


function onUpdatePreferences(savedConfig_)
	savedConfig = savedConfig_

	if savedConfig.checkSMD then
		unitData.smds.isActive = true
	else
		unitData.smds.isActive = false
		unitData.smds.savedUnits = {}
	end
	if savedConfig.checkOmni then
		unitData.omnis.isActive = true
	else
		unitData.omnis.isActive = false
		unitData.omnis.savedUnits = {}
	end
end


function addUnits()
	for _, group in unitData do
		for __,u in units.Get(group.category) do
			if not group.savedUnits[u:GetEntityId()] then
				group.savedUnits[u:GetEntityId()] = {
					unit = u,
					pos = u:GetPosition(),
				}
			end
		end
	end
end


function markPosition(pos)
	local time = savedConfig.markerDuration
	local size = 20

	ForkThread(function(pos, size, time)
		local s = UserDecal{}
		s:SetTexture('/env/utility/decals/objective_debug_albedo.dds')
		s:SetPositionByScreen(worldCamera:Project(pos))
		s:SetScale({size, size, size})
		WaitSeconds(time)
		s:Destroy()
	end, pos, size, time)
end