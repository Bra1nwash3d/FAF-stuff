local modpath = "/mods/reminder"

-----------------------------------------

local userSyncFunctions = {}

function addUserSyncFunction(f)
	table.insert(userSyncFunctions, f)
end

function onUserSync(syncTable)
	for _, f in userSyncFunctions do
		f(syncTable)
	end
end

-----------------------------------------

local commandIssuedFunctions = {}

function addCommandIssuedFunction(f)
	table.insert(commandIssuedFunctions, f)
end

function onOnCommandIssued(command)
	for _, f in commandIssuedFunctions do
		f(command)
	end
end

-----------------------------------------

