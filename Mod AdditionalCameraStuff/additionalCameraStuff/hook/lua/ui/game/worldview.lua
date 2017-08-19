local viewChangeListener = {}

local oldCreateMainWorldView = CreateMainWorldView
function CreateMainWorldView(parent, mapGroup, mapGroupRight)    
    oldCreateMainWorldView(parent, mapGroup, mapGroupRight)
    for _, f in viewChangeListener do
        f()
    end
end

function addViewChangeListener(f)
    table.insert(viewChangeListener, f)
end