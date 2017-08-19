local modpath = "/mods/reminder"
local utils = import(modpath..'/modules/notificationUtils.lua')

function getDefaultConfig()
	return {
		[1] = {
			name = "Starts at gametime (seconds):",
			value = 1800,
			path = "triggerAtSeconds",
			slider = {
				minVal = 20,
				maxVal = 60,
				valMult = 60,
			}
		},
		[2] = {
			name = "Retriggers each seconds:",
			value = 600,
			path = "retriggerDelay",
			slider = {
				minVal = 1,
				maxVal = 20,
				valMult = 60,
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
	text = "Antinuke",
	subtext = "Good to have",
	icons = {[1] = {icon='land_up.dds', isModFile=false}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	if not runtimeConfig.icons[2] then
		local faction = utils.getFaction()
		if faction == "UEF" then
			runtimeConfig.icons[2] = {icon='UEB4302_icon.dds', isModFile=false}
		elseif faction == "AEON" then
			runtimeConfig.icons[2] = {icon='UAB4302_icon.dds', isModFile=false}
		elseif faction == "CYBRAN" then
			runtimeConfig.icons[2] = {icon='URB4302_icon.dds', isModFile=false}
		else
			runtimeConfig.icons[2] = {icon='xsb4302_icon.dds', isModFile=false}
		end
	end

	return runtimeConfig
end


function onUpdatePreferences(savedConfig_)
end