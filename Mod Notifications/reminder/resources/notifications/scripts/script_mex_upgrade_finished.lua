local modpath = "/mods/reminder"
local utils = import(modpath..'/modules/notificationUtils.lua')
local units = import('/mods/common/units.lua')


function getDefaultConfig()
	return nil
end
local runtimeConfig = {
	text = "",
	subtext = "",
	icons = {[1] = {icon='land_up.dds', isModFile=false}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end

local allExtractors = {}

local t2Icon = nil
local t3Icon = nil


function init()
	local faction = utils.getFaction()
	if faction == "UEF" then
		t2Icon = {icon='UEB1202_icon.dds', isModFile=false}
		t3Icon = {icon='UEB1302_icon.dds', isModFile=false}
	elseif faction == "AEON" then
		t2Icon = {icon='UAB1202_icon.dds', isModFile=false}
		t3Icon = {icon='UAB1302_icon.dds', isModFile=false}
	elseif faction == "CYBRAN" then
		t2Icon = {icon='URB1202_icon.dds', isModFile=false}
		t3Icon = {icon='URB1302_icon.dds', isModFile=false}
	else
		t2Icon = {icon='XSB1202_icon.dds', isModFile=false}
		t3Icon = {icon='XSB1302_icon.dds', isModFile=false}
	end
end


function triggerNotification()
	local notificationIsReady = false
	runtimeConfig.unitsToSelect = {}

	-- add all new existing factories
	for _,u in units.Get(categories.MASSEXTRACTION) do
		if not u:IsDead() then
			if(u:IsInCategory("STRUCTURE"))then
				if(allExtractors[u:GetEntityId()] == nil) then
					allExtractors[u:GetEntityId()] = {unit = u, position = u:GetPosition()}
				end
			end
		end
	end
	
	-- remove dead ones... or are they finished upgrading?
	for id,v in allExtractors do
		if(v.unit:IsDead()) then
			-- same position as another unit? - upgrade done! - else dead
			local unitsWithSamePosition = {}
			for id2, v2 in allExtractors do
				if (id ~= id2) then
					if (v.position[1] == v2.position[1] and v.position[3] == v2.position[3]) then
						table.insert(unitsWithSamePosition, v2.unit)
						break
					end
				end
			end
			
			if table.getn(unitsWithSamePosition) > 0 then
				-- upgrade finished
				table.insert(runtimeConfig.unitsToSelect, utils.getLowestTechUnitsInGroup(unitsWithSamePosition)[1] )
			end
			
			allExtractors[id] = nil
		end
	end
	
	if table.getn(runtimeConfig.unitsToSelect) > 0 then
		if setRuntimeConfig() then
			notificationIsReady = true
		end
	end
	
	return notificationIsReady
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
end


function setRuntimeConfig()
	local t2 = 0
	local t3 = 0
	local text = ""
	for _, u in runtimeConfig.unitsToSelect do
		if not u:IsDead() then
			if u:IsInCategory("TECH3") then
				t3 = t3+1
			else
				t2 = t2+1
			end
		end
	end
	
	if t2 > 0 then
		text = text..t2.." T2"
		runtimeConfig.icons[2] = t2Icon
		if t3 > 0 then
			text = text.." and "..t3.." T3"
			runtimeConfig.icons[2] = t3Icon
		end
	else
		text = text..t3.." T3"
		runtimeConfig.icons[2] = t3Icon
	end
	
	if t2+t3 > 1 then
		runtimeConfig.text = "Mex Upgrades Finished"
		runtimeConfig.subtext = text..' Mex Upgrades finished!'
	elseif t2+t3 == 1 then
		runtimeConfig.text = "Mex Upgrade Finished"
		runtimeConfig.subtext = text..' Mex Upgrade finished!'
	else
		return false
	end
	return true
end