local OldFormatData = FormatData
local techCats = {
    [1] = "TECH1",
    [2] = "TECH2",
    [3] = "TECH3",
    [4] = "EXPERIMENTAL",
}

function FormatData(unitData, type)
    if type == 'selection' then
        local retData = {}

        local sortedUnits = {
            [1] = {cat = "ALLUNITS", units = {}},
            [2] = {cat = "LAND", units = {}},
            [3] = {cat = "AIR", units = {}},
            [4] = {cat = "NAVAL", units = {}},
            [5] = {cat = "STRUCTURE", units = {}},
            [6] = {cat = "SORTCONSTRUCTION", units = {}},
        }
        local lowFuelUnits = {}
        local idleConsUnits = {}
        for _, unit in unitData do
            local id = unit:GetBlueprint().BlueprintId

            if unit:IsInCategory('AIR') and unit:GetFuelRatio() < .2 and unit:GetFuelRatio() > -1 then
                if not lowFuelUnits[id] then
                    lowFuelUnits[id] = {}
                end
                table.insert(lowFuelUnits[id], unit)
            elseif options.gui_seperate_idle_builders ~= 0 and unit:IsInCategory('CONSTRUCTION') and unit:IsIdle() then
                if not idleConsUnits[id] then
                    idleConsUnits[id] = {}
                end
                table.insert(idleConsUnits[id], unit)
            else
                local cat = 0
                for i, t in sortedUnits do
                    if unit:IsInCategory(t.cat) then
                        cat = i
                    end
                end
                if not sortedUnits[cat].units[id] then
                    sortedUnits[cat].units[id] = {}
                end
                table.insert(sortedUnits[cat].units[id], unit)
            end
        end

        local didPutUnits = false
        for _, t in sortedUnits do
            if didPutUnits then
                table.insert(retData, { type = 'spacer' })
                didPutUnits = false
            end
            retData, didPutUnits = insertIntoTableLowestTechFirst(t.units, retData, false, false)
        end

        if didPutUnits then
            table.insert(retData, { type = 'spacer' })
            didPutUnits = false
        end
        retData, didPutUnits = insertIntoTableLowestTechFirst(lowFuelUnits, retData, true, false)

        if didPutUnits then
            table.insert(retData, { type = 'spacer' })
            didPutUnits = false
        end
        retData, didPutUnits = insertIntoTableLowestTechFirst(idleConsUnits, retData, false, true)

        if retData[table.getn(retData)].type == 'spacer' then 
            table.remove(retData, table.getn(retData))
        end

        CreateExtraControls('selection')
        SetSecondaryDisplay('attached')

        import(UIUtil.GetLayoutFilename('construction')).OnTabChangeLayout(type)
        return retData
    end

    return OldFormatData(unitData, type)
end

function insertIntoTableLowestTechFirst(units, t, isLowFuel, isIdleCon)
    local didInsert = false
    local isPut = false
    for _, tech in techCats do
        for i, v in units do
            if v[1]:IsInCategory(tech) then
                table.insert(t, { type = 'unitstack', id = i, units = v, lowFuel = isLowFuel, idleCon = isIdleCon })
                units[i] = nil
                isPut = true
                didInsert = true
            end
        end
    end
    --adding units without TECH category
    for i, v in units do
        table.insert(t, { type = 'unitstack', id = i, units = v, lowFuel = isLowFuel, idleCon = isIdleCon })
    end
    return t, didInsert
end