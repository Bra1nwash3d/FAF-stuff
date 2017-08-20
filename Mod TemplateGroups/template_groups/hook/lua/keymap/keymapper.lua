
local oldGenerateHotbuildModifiers = GenerateHotbuildModifiers
function GenerateHotbuildModifiers()
    local keyDetails = GetKeyMappingDetails()
    local modifiers = oldGenerateHotbuildModifiers()

    for key, info in keyDetails do
        if (info.action["category"] == "Template Groups") or (info.action["category"] == "hotbuildingExtra") then
            if key ~= nil then
                local modKey = "Shift-" .. key
                local modBinding = keyDetails[modKey]
                if not modBinding then
                    modifiers[modKey] = info.action
                end
            end
        end
    end
    return modifiers
end