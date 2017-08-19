local savedConfig = nil

function getDefaultConfig()
	return {
		[1] = {
			name = "Warn when having percentage of mass in storage:",
			value = 50,
			path = "percentageMass",
			slider = {
				minVal = 1,
				maxVal = 20,
				valMult = 5,
			}
		},
		[2] = {
			name = "Warn when having total mass in storage:",
			value = 5000,
			path = "totalMass",
			slider = {
				minVal = 1,
				maxVal = 20,
				valMult = 500,
			}
		},
	}
end
local runtimeConfig = {
	text = "Spend Mass",
	subtext = "You have a lot of mass in storage!",
	icons = {{icon='abstract/eco/massIcon.png', isModFile=true}},
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
	
	if( (econData["stored"]["MASS"] > ((econData["maxStorage"]["MASS"] * savedConfig.percentageMass)/100))
		or (econData["stored"]["MASS"] > savedConfig.totalMass)) then
		
		return true
	end
	return false
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
	savedConfig = savedConfig_
end