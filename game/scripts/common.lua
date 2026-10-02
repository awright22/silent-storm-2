-- SS2 helpers shared by every mission. The build puts this file in front of
-- each mission script, after the generated SS2_* constants.

-- Log line for build/shots/<name>.log and the in-game console.
function SS2_Log( text )
	out( "SS2: "..text )
end

-- The engine calls OnDialogFinished when the player closes a dialogue.
SS2_dialogsFinished = 0
function OnDialogFinished( code )
	SS2_dialogsFinished = SS2_dialogsFinished + 1
end

-- Play a dialogue and wait until the player has closed it.
-- In an unattended build (build.py --test or --skip-dialogue) nobody is there
-- to press Next, so the dialogue is only logged.
function SS2_Say( code )
	if SS2_SKIP_DIALOGUE then
		SS2_Log( "dialogue "..code )
		return
	end
	local before = SS2_dialogsFinished
	DialogPlay( code )
	while SS2_dialogsFinished == before do
		Sleep( 2 )
	end
end

-- Distance in tiles between a unit and a waypoint.
function SS2_DistanceTo( unit, waypoint )
	return GetDistance( GetPos( unit ), GetWaypointPos( waypoint ) )
end

-- 1 if any party member who can still fight is within radius tiles of the unit.
function SS2_PartyNear( unit, radius )
	local party = PlayerGetUnits( 0 )
	local i
	for i = 0, GroupGetSize( party ) - 1 do
		local member = GroupGetUnit( party, i )
		if UnitCanFight( member ) and GetDistance( GetPos( member ), GetPos( unit ) ) <= radius then
			return 1
		end
	end
	return nil
end

-- 1 if every party member who can still fight is within radius tiles of the
-- waypoint, and at least one can fight.
function SS2_PartyAt( waypoint, radius )
	local party = PlayerGetUnits( 0 )
	local count = 0
	local i
	for i = 0, GroupGetSize( party ) - 1 do
		local member = GroupGetUnit( party, i )
		if UnitCanFight( member ) then
			if SS2_DistanceTo( member, waypoint ) > radius then
				return nil
			end
			count = count + 1
		end
	end
	if count > 0 then
		return 1
	end
	return nil
end

-- 1 when the mission is running inside a campaign (it has a scenario zone),
-- nil when it was started on its own with "map <id>".
function SS2_InCampaign()
	if GetCurrentZoneAILevel() ~= nil then
		return 1
	end
	return nil
end
