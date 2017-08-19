local modpath = "/mods/reminder"
local utils = import(modpath..'/modules/notificationUtils.lua')
local units = import('/mods/common/units.lua')


function getDefaultConfig()
	return nil
end
local runtimeConfig = {
	text = "HQ Finished",
	subtext = "",
	icons = {},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end


local allFactories = {}


function init()
end


function triggerNotification()
	local notificationIsReady = false

	-- add all new existing factories
	for _,u in units.Get(categories.FACTORY) do
		if(u:IsInCategory("STRUCTURE"))then
			if(allFactories[u:GetEntityId()] == nil) then
				allFactories[u:GetEntityId()] = {unit = u, position = u:GetPosition()}
			end
		end
	end
	
	-- remove dead ones... or are they finished upgrading?
	for id,v in allFactories do
		if(v.unit:IsDead()) then
			-- same position as another unit? - upgrade done! - else dead
			local unitsWithSamePosition = {}
			for id2, v2 in allFactories do
				if (id ~= id2) then
					if (v.position[1] == v2.position[1] and v.position[3] == v2.position[3]) then
						table.insert(unitsWithSamePosition, v2.unit)
						break
					end
				end
			end
			
			if table.getn(unitsWithSamePosition) > 0 then
				-- upgrade finished
				if(setRuntimeConfig(utils.getLowestTechUnitsInGroup(unitsWithSamePosition)[1])) then
					runtimeConfig.unitsToSelect = {utils.getLowestTechUnitsInGroup(unitsWithSamePosition)[1]}
					notificationIsReady = true
				end
			end
			
			allFactories[id] = nil
		end
	end
	
	return notificationIsReady
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
end


---------------------


function setRuntimeConfig(u)
	if u:IsDead() then
		return false
	end

	runtimeConfig.icons[1] = {icon='land_up.dds', isModFile=false}
	local iKind = "Land"
	if(u:IsInCategory("AIR")) then
		iKind = "Air"
	elseif(u:IsInCategory("NAVAL")) then
		iKind = "Navy"
		runtimeConfig.icons[1] = {icon='sea_up.dds', isModFile=false}
	end
	
	local iTech = ""
	if(isT2Hq(u:GetBlueprint())) then
		iTech = "T2"
	elseif(isT3Hq(u:GetBlueprint())) then
		iTech = "T3"
	else
		return false
	end
	
	local searchForIcon = u:GetBlueprint().BlueprintId..'_icon.dds'
	runtimeConfig.icons[2] = {icon=searchForIcon, isModFile=false}
	runtimeConfig.subtext = iTech..' '..iKind..' HQ finished!'
	return true
end


function isT2Hq(bp)
	return cutBpId(bp.BlueprintId) == "020"
end
function isT3Hq(bp)
	return cutBpId(bp.BlueprintId) == "030"
end


function cutBpId(s)
   return string.sub(s, 4, 6)   
end