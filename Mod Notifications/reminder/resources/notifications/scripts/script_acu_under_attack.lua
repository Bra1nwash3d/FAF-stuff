local modpath = "/mods/reminder"
local units = import('/mods/common/units.lua')
local getEnh = import('/lua/enhancementcommon.lua')

local savedConfig = nil


function getDefaultConfig()
	return 	{
		[1] = {
			name = "Warn when losing percentage of health in 1 second:",
			value = 1,
			path = "warnAtPercentage",
			slider = {
				minVal = 1,
				maxVal = 50,
				valMult = 0.100000000,
			}
		},
		[2] = {
			name = "Warn when losing percentage of health in one strike:",
			value = 3,
			path = "warnAtPercentageInStrike",
			slider = {
				minVal = 10,
				maxVal = 100,
				valMult = 0.100000000,
			}
		},
	}
end
local runtimeConfig = {
	text = "ACU under attack!",
	subtext = "",
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
local acuBp = nil
local avg1s = 0
local previousHp = 0
local curPrevHp = 0
local previousShield = 0
local curPrevShield = 0

function init()
	for _,u in units.Get(categories.COMMAND) do
		acu = u
		previousHp = acu:GetHealth()
		curPrevHp = previousHp
		previousShield = 0
		curPrevShield = 0
		if u:IsInCategory("AEON") then
			runtimeConfig.icons[2] = {icon='UAL0001_icon.dds', isModFile=false}
		elseif u:IsInCategory("CYBRAN") then
			runtimeConfig.icons[2] = {icon='URL0001_icon.dds', isModFile=false}
		elseif u:IsInCategory("SERAPHIM") then
			runtimeConfig.icons[2] = {icon='XSL0001_icon.dds', isModFile=false}
		end
		acuBp = acu:GetBlueprint()
	end
	runtimeConfig.unitsToSelect = {acu}
end


function triggerNotification()
	if(acu == nil) then
		runtimeConfig.unitsToSelect = {}
		return false
	end
	if (acu:IsDead()) then
		acu = nil
		runtimeConfig.unitsToSelect = {}
		return false
	end
	
	curPrevHp = previousHp
	previousHp = acu:GetHealth()
	curPrevShield = previousShield
	if(acu:GetShieldRatio() > 0) then
		if acuBp.Defense.Shield.ShieldMaxHealth then
			previousShield = math.floor(acuBp.Defense.Shield.ShieldMaxHealth * acu:GetShieldRatio())
		else
			previousShield = math.floor(acuBp.Enhancements[getEnh.GetEnhancements(acu:GetEntityId()).Back].ShieldMaxHealth * acu:GetShieldRatio())
		end
	end
	
	avg1s = avg1s*0.9 - ((previousHp+previousShield) - (curPrevHp+curPrevShield))*0.1
	local acuMaxHealth = acu:GetMaxHealth()
	local acuCurHealth = acu:GetHealth()
	
	if(( (acuCurHealth+((savedConfig.warnAtPercentageInStrike*acuMaxHealth))/100) < curPrevHp)
		or ((curPrevShield+savedConfig.warnAtPercentageInStrike*acuMaxHealth) < curPrevShield )) then
		avg1s = 0
		setSubtext()
		return true
	end
	
	if ((acuMaxHealth*savedConfig.warnAtPercentage)/1000 < avg1s) then
		avg1s = 0
		setSubtext()
		return true
	end
	
	return false
end


function setSubtext()
	local acuHp = math.floor(acu:GetHealth())
	if (previousShield > 0) then
		runtimeConfig.subtext = math.floor(acu:GetHealth()).." (+"..previousShield..") hp remaining"
	else
		runtimeConfig.subtext = math.floor(acu:GetHealth()).." hp remaining"
	end
end


function onRetriggerDelay()
	if acu then
		avg1s = 0
		previousHp = acu:GetHealth()
		curPrevHp = previousHp
	end
end


function onUpdatePreferences(savedConfig_)
	savedConfig = savedConfig_
end