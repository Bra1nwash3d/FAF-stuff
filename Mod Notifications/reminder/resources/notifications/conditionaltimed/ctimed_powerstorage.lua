local modpath = "/mods/reminder"
local utils = import(modpath..'/modules/notificationUtils.lua')

function getDefaultConfig()
	return {
		[1] = {
			name = "Starts at gametime (seconds):",
			value = 480,
			path = "triggerAtSeconds",
			slider = {
				minVal = 0,
				maxVal = 40,
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
	text = "Power Storage",
	subtext = "Good to have",
	icons = {[1] = {icon='land_up.dds', isModFile=false}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	if not runtimeConfig.icons[2] then
		local faction = utils.getFaction()
		if faction == "UEF" then
			runtimeConfig.icons[2] = {icon='UEB1105_icon.dds', isModFile=false}
		elseif faction == "AEON" then
			runtimeConfig.icons[2] = {icon='UAB1105_icon.dds', isModFile=false}
		elseif faction == "CYBRAN" then
			runtimeConfig.icons[2] = {icon='URB1105_icon.dds', isModFile=false}
		else
			runtimeConfig.icons[2] = {icon='XSB1105_icon.dds', isModFile=false}
		end
	end

	return runtimeConfig
end


function triggerNotification()
	if GetEconomyTotals()["maxStorage"]["ENERGY"] < 5000 then
		return true
	end
	return false
end


function onUpdatePreferences(savedConfig)
end