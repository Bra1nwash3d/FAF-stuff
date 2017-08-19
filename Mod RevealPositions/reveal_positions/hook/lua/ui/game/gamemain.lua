local Button = import('/lua/maui/button.lua').Button

local disappearTimeIfObs = 40


ForkThread(function()
	WaitSeconds(3)
	while GetGameTimeSeconds() < 3 do
		WaitSeconds(0.1)
	end

	local saveData = {}
	doscript('/lua/dataInit.lua', saveData)
	doscript(SessionGetScenarioInfo().save, saveData)

	startPositions = {}
	for markerName, markerTable in saveData.Scenario.MasterChain['_MASTERCHAIN_'].Markers do
		if string.find(markerName, "ARMY_*") then
			startPositions[markerName] = markerTable.position
		end
	end
	
	local factions = {
		[0] = "UEF",
		[1] = "Aeon",
		[2] = "Cybran",
		[3] = "Sera"
	}

	local removeAtTime = false
	if GetFocusArmy() < 0 then
		removeAtTime = disappearTimeIfObs
	end
	for armyIndex, armyData in GetArmiesTable().armiesTable do
		if (not armyData.civilian) and (not isAllyOrObs(GetFocusArmy(), armyIndex)) then
			local armyName = armyData.nickname
			if armyData.faction >= 0 and armyData.faction <= table.getn(factions) then
				armyName = armyName..' ['..factions[armyData.faction]..']'
			end
			createPositionMarker(armyName, startPositions[armyData.name][1], startPositions[armyData.name][2], startPositions[armyData.name][3], removeAtTime)
		end
	end    
end)


function isAllyOrObs(army1, army2)
	if army1 < 0 then
		return false -- need false so that we have labels for all players
	end
	return IsAlly(army1, army2)
end


function createPositionMarker(armyName, posX, posY, posZ, removeAtTime)
	if (not posX) or (not posY) or (not posZ) then
		return 
	end 
	local pos = Vector(posX, posY, posZ)

	local posMarker = Bitmap(GetFrame(0))
	posMarker.Width:Set(150)
	posMarker.Height:Set(25)
	posMarker.pos = pos
	posMarker.Depth:Set(10)
	posMarker:SetNeedsFrameUpdate(true)

	local posMarkerButton = Button(posMarker, '/mods/reveal_positions/textures/bg.png', '/mods/reveal_positions/textures/bg.png', '/mods/reveal_positions/textures/bg.png', '/mods/reveal_positions/textures/bg.png')
	posMarkerButton.Width:Set(150)
	posMarkerButton.Height:Set(25)
	posMarkerButton.pos = pos
	posMarkerButton.Depth:Set(11)

	posMarkerButton:EnableHitTest(true)
	posMarkerButton.OnClick = function(self, event)
		posMarker:Destroy()
		posMarker = nil
		posMarkerButton:Destroy()
		posMarkerButton = nil
	end

	local defaultOnFrame = function(self, delta)
		local worldView = import('/lua/ui/game/worldview.lua').viewLeft
		local pos = worldView:Project(Vector(posMarker.pos.x, posMarker.pos.y, posMarker.pos.z))
		LayoutHelpers.AtLeftTopIn(posMarker, worldView, pos.x - posMarker.Width() / 2, pos.y - posMarker.Height() / 2 + 1)
		LayoutHelpers.AtLeftTopIn(posMarkerButton, worldView, pos.x - posMarker.Width() / 2, pos.y - posMarker.Height() / 2 + 1)
	end

	if removeAtTime then
		posMarker.OnFrame = function(self, delta)
			defaultOnFrame(self, delta)
			if (GetGameTimeSeconds() > removeAtTime) then
				posMarker:Destroy()
				posMarker = nil
				posMarkerButton:Destroy()
				posMarkerButton = nil  
			end
		end
	else
		posMarker.OnFrame = function(self, delta)
			defaultOnFrame(self, delta)
		end
	end
		
	posMarker.armyName = UIUtil.CreateText(posMarker, armyName, 12, UIUtil.bodyFont)
	posMarker.armyName:SetColor('white')
	posMarker.armyName:SetDropShadow(true)
	LayoutHelpers.AtCenterIn(posMarker.armyName, posMarker, 0, 0)
	return posMarker
end