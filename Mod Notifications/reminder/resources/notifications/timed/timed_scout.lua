local modpath = "/mods/reminder"
local utils = import(modpath..'/modules/notificationUtils.lua')
local units = import('/mods/common/units.lua')

function getDefaultConfig()
	return {
		[1] = {
			name = "Starts at gametime (seconds):",
			value = 600,
			path = "triggerAtSeconds",
			slider = {
				minVal = 0,
				maxVal = 30,
				valMult = 30,
			}
		},
		[2] = {
			name = "Retriggers each seconds:",
			value = 120,
			path = "retriggerDelay",
			slider = {
				minVal = 0,
				maxVal = 20,
				valMult = 15,
			}
		},
		[3] = {
			name = "Will trigger more than just once",
			path = "canRetrigger",
			value = true,
		},
	}
end

local runtimeConfig = {
	text = "Scout!",
	subtext = "Scouting saves lives",
	icons = {[1] = {icon='air_up.dds', isModFile=false}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	if not runtimeConfig.icons[2] then
		local faction = utils.getFaction()
		if faction == "UEF" then
			runtimeConfig.icons[2] = {icon='UEA0302_icon.dds', isModFile=false}
		elseif faction == "AEON" then
			runtimeConfig.icons[2] = {icon='UAA0302_icon.dds', isModFile=false}
		elseif faction == "CYBRAN" then
			runtimeConfig.icons[2] = {icon='URA0302_icon.dds', isModFile=false}
		else
			runtimeConfig.icons[2] = {icon='XSA0302_icon.dds', isModFile=false}
		end
	end

	setUnitsToSelect()
	return runtimeConfig
end


function setUnitsToSelect()
	runtimeConfig.unitsToSelect = {}
	for _,u in units.Get(categories.AIR) do
		if(u:IsInCategory("INTELLIGENCE"))then
			if(u:IsIdle())then
				table.insert(runtimeConfig.unitsToSelect, u)
			end
		end	
	end
end


function onUpdatePreferences(savedConfig_)
end