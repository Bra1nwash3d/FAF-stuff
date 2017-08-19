local modpath = "/mods/reminder"
local savedConfig = nil


function getDefaultConfig()
	return {
		[1] = {
			name = "Check T3 Engineers",
			path = "t3Engy",
			value = true,
		},
		[2] = {
			name = "Check T2 Engineers",
			path = "t2Engy",
			value = true,
		},
		[3] = {
			name = "Check T1 Engineers",
			path = "t1Engy",
			value = false,
		},
	}
end
local runtimeConfig = {
	text = "",
	subtext = "",
	icons = {[1] = {icon='amph_up.dds', isModFile=false},
			 [3] = {icon='abstract/idle.png', isModFile=true}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end

local cats = {
	[1] = {name="T3", category="TECH3"},
	[2] = {name="T2", category="TECH2"},
	[3] = {name="T1", category="TECH1"},
}
function catsRemoveOrInsert(boolValue, i, value)
	if boolValue == true then
		cats[i] = value
	else
		cats[i] = nil
	end
end


function init()
end


function triggerNotification()
	runtimeConfig.unitsToSelect = {}

	for _, catValues in cats do
		for _,u in GetIdleEngineers() or {} do
			if(u:IsInCategory(catValues.category) )then
				table.insert(runtimeConfig.unitsToSelect, u)
			end	
		end
		
		num = table.getn(runtimeConfig.unitsToSelect)
		if num > 0 then
			runtimeConfig.text = "Idle Engineer"
			amountText = "engy"
			if(num > 1) then
				runtimeConfig.text = "Idle Engineers"
				amountText = "engies"
			end
			
			local searchForIcon = runtimeConfig.unitsToSelect[1]:GetBlueprint().BlueprintId..'_icon.dds'
			runtimeConfig.icons[2] = {icon=searchForIcon, isModFile=false}
			runtimeConfig.subtext = num.." idle "..catValues.name.." "..amountText
			return true
		end
	end
	
	return false
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
	savedConfig = savedConfig_
	catsRemoveOrInsert(savedConfig.t3Engy, 1, {name="T3", category="TECH3"})
	catsRemoveOrInsert(savedConfig.t2Engy, 2, {name="T2", category="TECH2"})
	catsRemoveOrInsert(savedConfig.t1Engy, 3, {name="T1", category="TECH1"})
end