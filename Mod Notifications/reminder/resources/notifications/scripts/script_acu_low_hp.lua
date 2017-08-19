local modpath = "/mods/reminder"
local units = import('/mods/common/units.lua')
local savedConfig = nil

function getDefaultConfig()
	return 	{
		[1] = {
			name = "Warn at percentage of health:",
			value = 20,
			path = "warnAtPercentage",
			slider = {
				minVal = 10,
				maxVal = 50,
				valMult = 1,
			}
		},
	}
end
local runtimeConfig = {
	text = "Low ACU hp",
	subtext = "Your ACU has low health!",
	icons = {[1] = {icon='amph_up.dds', isModFile=false},
			 [2] = {icon='UEL0001_icon.dds', isModFile=false},
			 [3] = {icon='abstract/attacked.png', isModFile=true}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end

local acu = nil


function init()
	for _,u in units.Get(categories.COMMAND) do
		acu = u
		if u:IsInCategory("AEON") then
			runtimeConfig.icons[2] = {icon='UAL0001_icon.dds', isModFile=false}
		elseif u:IsInCategory("CYBRAN") then
			runtimeConfig.icons[2] = {icon='URL0001_icon.dds', isModFile=false}
		elseif u:IsInCategory("SERAPHIM") then
			runtimeConfig.icons[2] = {icon='XSL0001_icon.dds', isModFile=false}
		end
	end
	runtimeConfig.unitsToSelect = {acu}
end


function triggerNotification()
	if (acu == nil) then
		runtimeConfig.unitsToSelect = {}
		return false
	end
	if (acu:IsDead()) then
		acu = nil
		runtimeConfig.unitsToSelect = {}
		return false
	end
	
	if ( acu:GetHealth() < acu:GetMaxHealth()*(savedConfig.warnAtPercentage/100) ) then
		return true
	end
	
	return false
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
	savedConfig = savedConfig_
end