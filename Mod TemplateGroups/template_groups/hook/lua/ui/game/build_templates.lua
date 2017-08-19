local currentFilterKey = false

function SetFilterKey(key)
	currentFilterKey = key
end

function GetTemplates()
	if currentFilterKey then
		local templates = {}
		for i,template in Prefs.GetFromCurrentProfile('build_templates') do
			if template.name.sub(template.name,1,1) == ''..currentFilterKey then
				templates[i] = template
			end
		end
		return templates
	end
    return Prefs.GetFromCurrentProfile('build_templates')
end