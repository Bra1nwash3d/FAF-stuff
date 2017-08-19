local modpath = "/mods/additionalCameraStuff/"
local ASCUI = import(modpath..'modules/ACSUI.lua')

local originalCreateUI = CreateUI
local originalSetLayout = SetLayout


function CreateUI(isReplay) 
	originalCreateUI(isReplay)
	import('/mods/additionalCameraStuff/modules/ACSmain.lua').init()
end

function SetLayout(layout)
	originalSetLayout(layout)
	ASCUI.SetLayout()
end