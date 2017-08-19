function containsKey(t, key)
    return (t[key] ~= nil)
end

function containsValue(t, value)
    for _, v in t do
        if v == value then
            return true
        end
    end
    return false
end

