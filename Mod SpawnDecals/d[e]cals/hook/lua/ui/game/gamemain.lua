local decals_modpath = "/mods/d[e]cals/"

local originalCreateUI = CreateUI 
function CreateUI(isReplay) 
	originalCreateUI(isReplay)
	ForkThread(import(decals_modpath..'modules/decals.lua').init)
end