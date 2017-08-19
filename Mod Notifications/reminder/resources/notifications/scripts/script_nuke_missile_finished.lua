local units = import('/mods/common/units.lua')


function getDefaultConfig()
	return nil
end
local runtimeConfig = {
	text = "Nuke is ready",
	subtext = "",
	icons = {{icon='abstract/nuke/nuke.png', isModFile=true}},
	unitsToSelect = {},
	sound = false,
}
function getRuntimeConfig()
	return runtimeConfig
end


local missileCountStationary = 0
local missileCountMobile = 0


function init()
end


function triggerNotification()
	local currentMissilesStationary = 0
	local currentMissilesMobile = 0
	runtimeConfig.unitsToSelect = {}
	
	for _,u in units.Get(categories.NUKE) do
		info = u:GetMissileInfo()
		if(u:IsInCategory("STRUCTURE") )then
			currentMissilesStationary = currentMissilesStationary + info.nukeSiloStorageCount
		else
			currentMissilesMobile = currentMissilesMobile + info.nukeSiloStorageCount
		end
		
		if( info.nukeSiloStorageCount > 0 ) then
			table.insert(runtimeConfig.unitsToSelect, u)
		end
	end
	
	if(currentMissilesStationary > missileCountStationary) then
		missileCountStationary = currentMissilesStationary
		runtimeConfig.subtext = "A stationary nuke is ready"
		return true
	end
	missileCountStationary = currentMissilesStationary
	
	if(currentMissilesMobile > missileCountMobile) then
		missileCountMobile = currentMissilesMobile
		runtimeConfig.subtext = "A mobile nuke is ready"
		return true
	end
	missileCountMobile = currentMissilesMobile
	
	return false
end


function onRetriggerDelay()
end


function onUpdatePreferences(savedConfig_)
end