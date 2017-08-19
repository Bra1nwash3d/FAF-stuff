local Button = import('/lua/maui/button.lua').Button


ForkThread(function()
	WaitSeconds(3)
	while GetGameTimeSeconds() < 3 do
		WaitSeconds(0.1)
	end
    local spawn = SessionGetScenarioInfo().Options.TeamSpawn
    if spawn and table.find({'random', 'balanced', 'balanced_flex', 'random_reveal', 'balanced_reveal', 'balanced_flex_reveal'}, spawn) then
        return
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

	local armyTable = GetArmiesTable().armiesTable
	local armyfocus = GetFocusArmy()
    local factions = {
        [0] = "UEF",
        [1] = "Aeon",
        [2] = "Cybran",
        [3] = "Sera",
        [4] = "Nomads"
    }
    for armyIndex, armyData in armyTable do
        local generateMarker = true
        if armyfocus > -1 then
            if IsAlly(GetFocusArmy(), armyIndex) then
                generateMarker = false
            end
        end
        if armyData.civilian then
            generateMarker = false
        end
        if generateMarker then
            local armyName = armyData.nickname
            if armyData.faction >= 0 and armyData.faction <= table.getn(factions) then
                armyName = armyName..' ['..factions[armyData.faction]..']'
            end
            createPositionMarker(armyName, startPositions[armyData.name][1], startPositions[armyData.name][2], startPositions[armyData.name][3], armyfocus == -1, table.getn(armyTable) )
        end
    end
end)


function createPositionMarker(armyName, posX, posY, posZ, replay, playercount)
	if not (posX or posY or posZ) then
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
    posMarker.desintegrate = replay
    posMarker.playercount = playercount

	posMarkerButton:EnableHitTest(true)
	posMarkerButton.OnClick = function(self, event)
		posMarker:Destroy()
		posMarker = nil
		posMarkerButton:Destroy()
		posMarkerButton = nil
	end

	posMarker.OnFrame = function(self, delta)
		local worldView = import('/lua/ui/game/worldview.lua').viewLeft
		local pos = worldView:Project(Vector(posMarker.pos.x, posMarker.pos.y, posMarker.pos.z))

		LayoutHelpers.AtLeftTopIn(posMarker, worldView, pos.x - posMarker.Width() / 2, pos.y - posMarker.Height() / 2 + 1)
		LayoutHelpers.AtLeftTopIn(posMarkerButton, worldView, pos.x - posMarker.Width() / 2, pos.y - posMarker.Height() / 2 + 1)
        if GetGameTimeSeconds() > self.playercount*10 and self.desintegrate then
            posMarker:Destroy()
            posMarker = nil
            posMarkerButton:Destroy()
            posMarkerButton = nil  
        end
	end
		
	posMarker.armyName = UIUtil.CreateText(posMarker, armyName, 12, UIUtil.bodyFont)
	posMarker.armyName:SetColor('white')
	posMarker.armyName:SetDropShadow(true)
	LayoutHelpers.AtCenterIn(posMarker.armyName, posMarker, 0, 0)
	return posMarker
end