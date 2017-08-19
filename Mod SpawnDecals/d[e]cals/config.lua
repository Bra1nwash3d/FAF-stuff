layouts = {
	-- we have personal,clanicon,clanlabel,faction
	strategy_full = {
		player = {
			offset = {x=0, z=0},
			size = {x=15, z=15},
		},
		clanicon = false,
		clanlabel = {
			offset = {x=0, z=5},
			size = {x=15, z=5},
		},
		faction = {
			offset = {x=10, z=5},
			size = {x=5, z=5},
		},
	},

	-- we have personal/clanicon,clanlabel,faction
	strategy_clanicon = {
		mid = {
			offset = {x=0, z=0},
			size = {x=15, z=15},
		},
		clanlabel = {
			offset = {x=0, z=5},
			size = {x=15, z=5},
		},
		faction = {
			offset = {x=10, z=5},
			size = {x=5, z=5},
		},
	},

	-- just faction
	strategy_faction = {
		faction = {
			offset = {x=0, z=0},
			size = {x=12, z=12},
		},
	},

}

misc = {
	-- false or "<clantag>"
	allOtherClansArePeasants = false,
	-- false or true
	allNonClanMembersArePeasants = false,
}

-- just pic names, for weird reasons they need to be hardcoded
factionNames = {"uef", "aeon", "cybran", "sera"}

-- shows simple squares for player
testmode = "washy"