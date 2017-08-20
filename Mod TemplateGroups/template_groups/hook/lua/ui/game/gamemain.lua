

local originalCreateUI_templategroups = CreateUI 
function CreateUI(isReplay)
	originalCreateUI_templategroups(isReplay)
	local KeyMapper = import('/lua/keymap/keymapper.lua')
	for i = 1, 5 do
		local s = ''..i
		KeyMapper.SetUserKeyAction(
			"Templates beginning with "..s,
			{
				action = "UI_Lua import('/lua/keymap/hotbuild.lua').buildActionTemplate(0, "..s..")",
				category = "Template Groups",
				order = i,
			}
		)
	end
end