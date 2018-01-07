local rainbowColourPlayerNicks = import('/mods/rainbow_colour/names.lua').names
local colours = {
	{0, 255, 0},	-- green
	{128, 255, 0},	-- green-yellowish
	{255, 255, 0},	-- yellow
	{255, 128, 0},	-- orange
	{255, 0, 0},	-- red
	{255, 0, 127},	-- pink
	{255, 0, 255},	-- more pink
	{127, 0, 255},	-- purple
	{0, 0, 255},	-- blue
	{0, 128, 255},	-- light blue
	{0, 255, 255},	-- cyan
	{0, 255, 128},	-- green-blueish
}

function getPlayerTable(nick, offset)
	local p = {}
	p.nick = nick
	p.cur = math.min(math.max(offset, 1), table.getn(colours))
	p.curstep = 0
	p.totalsteps = 25
	p.r = 0
	p.g = 0
	p.b = 0
	p.c1 = false
	p.c2 = false
	p.curnext = p.cur + 1
	if p.curnext > table.getn(colours) then
		p.curnext = 1
	end
	return p
end

function nextRGB(p)
	p.c1 = colours[p.cur]
	p.c2 = colours[p.curnext]
	d = p.curstep/p.totalsteps
	p.r = p.c1[1] + d*(p.c2[1]-p.c1[1])
	p.g = p.c1[2] + d*(p.c2[2]-p.c1[2])
	p.b = p.c1[3] + d*(p.c2[3]-p.c1[3])
	p.curstep = p.curstep + 1
	if p.curstep >= p.totalsteps then
		p.curstep = 0
		p.cur = p.curnext
		p.curnext = p.curnext + 1
		if p.curnext > table.getn(colours) then
			p.curnext = 1
		end
	end
end

local defaultBeginSession = BeginSession
function BeginSession()
	defaultBeginSession()
	for iArmy, strArmy in pairs(ListArmies()) do
		for _, player in rainbowColourPlayerNicks do
			if player.nick == ArmyBrains[iArmy].Nickname then
				p = getPlayerTable(player.nick, player.offset)
				ForkThread(function(iArmy, sArmy, p)
					while true do
						WaitSeconds(0.1)
						nextRGB(p)
						SetArmyColor(sArmy, p.r, p.g, p.b)
					end
				end, iArmy, strArmy, p)
				break
			end
		end
	end
end
