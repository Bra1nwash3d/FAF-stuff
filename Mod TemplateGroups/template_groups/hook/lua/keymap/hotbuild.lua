local Templates = import('/lua/ui/game/build_templates.lua')

local buildActionTemplate_old = buildActionTemplate
function buildActionTemplate(modifier, nameStart)
    if GetSelectedUnits() then
        -- would be nicer without the SetFilterKey function, but destructively
        -- hooking the whole buildActionTemplate function is even worse
        Templates.SetFilterKey(nameStart)
        buildActionTemplate_old(modifier)
        Templates.SetFilterKey(false)
    end
end