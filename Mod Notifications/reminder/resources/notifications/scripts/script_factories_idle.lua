local modpath = "/mods/reminder"
local savedConfig


function getDefaultConfig()
	return {
		[1] = {
			name = "Check T3 Factories",
			path = "t3factory",
			value = true,
		},
		[2] = {
			name = "Check T2 Factories",
			path = "t2factory",
			value = true,
		},
		[3] = {
			name = "Check T1 Factories",
			path = "t1factory",
			value = true,
		},
	}
end
local runtimeConfig = {
	text = "",
	subtext = "",
	icons = {[3] = {icon='abstract/idle.png', isModFile=true}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end


local cats = {
	[1] = {name="T3", category="TECH3"},
	[2] = {name="T2", category="TECH2"},
	[2] = {name="T1", category="TECH1"},
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
		for _,u in GetIdleFactories() or {} do
			if(u:IsInCategory(catValues.category))then
				table.insert(runtimeConfig.unitsToSelect, u)
			end	
		end
		
		num = table.getn(runtimeConfig.unitsToSelect)
		if num > 0 then
			runtimeConfig.text = "Idle Factory"
			amountText = "factory"
			if(num > 1) then 
				runtimeConfig.text = "Idle Factories"
				amountText = "factories"
			end
			
			local searchForIcon = runtimeConfig.unitsToSelect[1]:GetBlueprint().BlueprintId..'_icon.dds'
			runtimeConfig.icons[2] = {icon=searchForIcon, isModFile=false}
			if(runtimeConfig.unitsToSelect[1]:IsInCategory("NAVAL")) then
				runtimeConfig.icons[1] = {icon='sea_up.dds', isModFile=false}
			else
				runtimeConfig.icons[1] = {icon='land_up.dds', isModFile=false}
			end
			
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
	catsRemoveOrInsert(savedConfig.t3factory, 1, {name="T3", category="TECH3"})
	catsRemoveOrInsert(savedConfig.t2factory, 2, {name="T2", category="TECH2"})
	catsRemoveOrInsert(savedConfig.t1factory, 3, {name="T1", category="TECH1"})
end