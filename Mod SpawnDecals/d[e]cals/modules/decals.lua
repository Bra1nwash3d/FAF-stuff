local modpath = "/mods/d[e]cals/"
local units = import('/mods/common/units.lua')
local Decal = import('/lua/user/userdecal.lua').UserDecal
local sessionInfo = SessionGetScenarioInfo()

local layouts = import(modpath..'config.lua').layouts
local misc = import(modpath..'config.lua').misc
local factionNames = import(modpath..'config.lua').factionNames
local testmode = import(modpath..'config.lua').testmode

local decalpaths = {
	clan_icons = modpath.."decals/clan_icons/",
	clan_labels = modpath.."decals/clan_labels/",
	factions = modpath.."decals/factions/",
	players = modpath.."decals/players/",
	misc = modpath.."decals/misc/",
	--death = modpath.."decals/death/",
}
local decals = {
	players = {},
	clan_icons = {},
	clan_labels = {},
	factions = {},
	misc = {},
	--death = {},
}


function init()
	initDecalLists()
	ForkThread(function()
		local saveData = {}
		doscript('/lua/dataInit.lua', saveData)
		doscript(SessionGetScenarioInfo().save, saveData)

		local armyTable = GetArmiesTable().armiesTable
		local startPositions = {}
		for markerName, markerTable in saveData.Scenario.MasterChain['_MASTERCHAIN_'].Markers do
			if string.find(markerName, "ARMY_*") then
				startPositions[markerName] = markerTable.position
			end
		end
		for armyIndex, armyData in armyTable do
			if (not armyData.civilian) then
				local pos = Vector(startPositions[armyData.name][1], startPositions[armyData.name][2], startPositions[armyData.name][3])
				placeSpawnIcons(armyData, pos)
			end
		end
	end)
end


function getDecalsInPath(path)
	local decals = {}
	for i, file in DiskFindFiles(path, "*") do
		decals[file] = file
	end
	return decals
end


function initDecalLists()
	decals.clan_icons = getDecalsInPath(decalpaths.clan_icons)
	decals.clan_labels = getDecalsInPath(decalpaths.clan_labels)
	decals.factions = getDecalsInPath(decalpaths.factions)
	decals.players = getDecalsInPath(decalpaths.players)
	decals.misc = getDecalsInPath(decalpaths.misc)
	--death = getDecalsInPath(decalpaths.death)
end 


function placeSpawnIcons(armyData, pos)
	local playerName = armyData.nickname.lower(armyData.nickname)
	local clanIconPath, clanLabelPath = nil, nil
	local factionIconPath = decals.factions[decalpaths.factions..factionNames[armyData.faction+1]..'.dds']
	local playerIconPath = decals.players[decalpaths.players..playerName..'.dds']
	
	local playerClan = sessionInfo.Options.ClanTags[armyData.nickname]
	if playerClan and playerClan ~= "" then
		LOG('in clan '..playerClan)
		playerClan = playerClan.lower(playerClan)
		if misc.allOtherClansArePeasants and misc.allOtherClansArePeasants ~= playerClan then
			clanIconPath = decals.misc[decalpaths.misc..'peasantclan.dds']
		else
			clanIconPath = decals.clan_icons[decalpaths.clan_icons..playerClan..'.dds']
			clanLabelPath = decals.clan_labels[decalpaths.clan_labels..playerClan..'.dds']
		end
	else
		if misc.allNonClanMembersArePeasants then
			clanIconPath = decals.misc[decalpaths.misc..'noclan.dds']
		end
	end

	if playerName == testmode then
		playerIconPath = modpath.."decals/test/player.dds"
		factionIconPath = modpath.."decals/test/faction.dds"
		clanIconPath = modpath.."decals/test/clan_icon.dds"
		clanLabelPath = modpath.."decals/test/clan_label.dds"
	end

	-- layout strategies, depending on what we have
	-- personal icon in center
	if playerIconPath ~= nil then
		strategy_full(pos, playerIconPath, clanIconPath, clanLabelPath, factionIconPath)
		return
	end
	if clanIconPath ~= nil then
		strategy_clanicon(pos, clanIconPath, clanLabelPath, factionIconPath)
		return
	end
	strategy_faction(pos, factionIconPath)
end


function createDecalSimple(path, pos, offsets, sizes)
	local newdecal = Decal(GetFrame(0))
	newdecal:SetTexture(path)
	newdecal:SetScale({sizes.x, 0, sizes.z})
	local decalpos = Vector(pos.x + offsets.x, pos.y, pos.z + offsets.z)
	newdecal:SetPosition(decalpos)
end


----------------------
-- strategies for icon sizes + layouts (config contains all offsets/sizes)
-- the parameters are the paths

function strategy_full(pos, player, clanicon, clanlabel, faction)
	--LOG('strategy: strategy_full')
	local l = layouts.strategy_full
	if player and l.player then
		createDecalSimple(player, pos, l.player.offset, l.player.size)
	end
	if clanicon and l.clanicon then
		createDecalSimple(clanicon, pos, l.clanicon.offset, l.clanicon.size)
	end
	if clanlabel and l.clanlabel then
		createDecalSimple(clanlabel, pos, l.clanlabel.offset, l.clanlabel.size)
	end
	if faction and l.faction then
		createDecalSimple(faction, pos, l.faction.offset, l.faction.size)
	end
end


function strategy_clanicon(pos, mid, clanlabel, faction)
	--LOG('strategy: strategy_clanicon')
	local l = layouts.strategy_clanicon
	if mid and l.mid then
		createDecalSimple(mid, pos, l.mid.offset, l.mid.size)
	end
	if clanlabel and l.clanlabel then
		createDecalSimple(clanlabel, pos, l.clanlabel.offset, l.clanlabel.size)
	end
	if faction and l.faction then
		createDecalSimple(faction, pos, l.faction.offset, l.faction.size)
	end
end


function strategy_faction(pos, factionIconPath)
	--LOG('strategy: strategy_faction')
	local l = layouts.strategy_faction
	if factionIconPath and l.faction then
		createDecalSimple(factionIconPath, pos, l.faction.offset, l.faction.size)
	end
end