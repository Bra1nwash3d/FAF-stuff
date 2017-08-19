local modpath = "/mods/reminder"
local alreadyCounting = 0
local savedConfig = nil


function getDefaultConfig()
	return {
		[1] = {
			name = "Overflowing percentage more than using:",
			value = 20,
			path = "overflowPercentage",
			slider = {
				minVal = 5,
				maxVal = 50,
				valMult = 1,
			}
		},
		[2] = {
			name = "Warn after seconds of continuous overflow:",
			value = 10,
			path = "continuousSeconds",
			slider = {
				minVal = 1,
				maxVal = 30,
				valMult = 1,
			}
		},
	}
end
local runtimeConfig = {
	text = "Spend Energy",
	subtext = "You are overflowing energy!",
	icons = {{icon='abstract/eco/energyIcon.png', isModFile=true}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end

function init()
end

function triggerNotification()
	econData = GetEconomyTotals()
	
	if( ((econData["stored"]["ENERGY"] + 1) > econData["maxStorage"]["ENERGY"])
		and (econData["income"]["ENERGY"] > (econData["lastUseRequested"]["ENERGY"]*(1 + savedConfig.overflowPercentage/10)) ) ) then

		alreadyCounting = alreadyCounting + 0.1	
		if(alreadyCounting > (savedConfig.continuousSeconds)) then
			alreadyCounting = 0
			return true
		end
	else
		alreadyCounting = 0
	end
	return false
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
	savedConfig = savedConfig_
end