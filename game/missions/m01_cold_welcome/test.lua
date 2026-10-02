-- Scripted playthrough of mission 1, compiled in only by "build.py --test".
-- It does what a player would have to achieve, by fiat, and checks that the
-- mission's own logic reacts: house guards down and a team member next to
-- Olsen frees him; the whole team at the tree line completes the mission.

function M01_TestFail( why )
	SS2_Log( "TEST FAIL: "..why )
end

-- How many of the team this hostile unit can see right now.
function M01_SeenBy( enemy, party )
	local count = 0
	local i
	for i = 0, GroupGetSize( party ) - 1 do
		if UnitIsSeeUnit( enemy, GroupGetUnit( party, i ) ) then
			count = count + 1
		end
	end
	return count
end

function M01_Test()
	local party = PlayerGetUnits( 0 )
	local i, t
	GroupCheat( party, CHEAT_GODMODE, 1 )

	-- The stealth route only exists if the team arrives unseen. Watch for ten
	-- seconds while the sentry walks his beat: nobody may see the team where it
	-- stands, and no fight may start.
	for t = 1, 10 do
		Sleep( 20 )
		for i = 0, GroupGetSize( yardGuards ) - 1 do
			if M01_SeenBy( GroupGetUnit( yardGuards, i ), party ) > 0 then
				M01_TestFail( "a yard guard sees the team at its arrival point, "..t.." s in" )
				return
			end
		end
		for i = 0, GroupGetSize( houseGuards ) - 1 do
			if M01_SeenBy( GroupGetUnit( houseGuards, i ), party ) > 0 then
				M01_TestFail( "a house guard sees the team at its arrival point, "..t.." s in" )
				return
			end
		end
		if not IsRealTime() then
			M01_TestFail( "a fight started while the team stood at its arrival point, "..t.." s in" )
			return
		end
	end
	SS2_Log( "TEST step: team unseen at the arrival point for 10 s" )

	if m01_state ~= "rescue" then
		M01_TestFail( "expected state rescue at start, got "..m01_state )
		return
	end
	if not IsValid( olsen ) or UnitIsDead( olsen ) then
		M01_TestFail( "Olsen is missing or dead at start" )
		return
	end
	if GroupGetSize( houseGuards ) ~= 2 or GroupGetSize( yardGuards ) ~= 4 then
		M01_TestFail( "expected 2 house guards and 4 in the yard" )
		return
	end

	-- A team member reaches Olsen while his guards are alive: he must not be freed yet.
	UnitSetToWaypoint( GetHero(), "m01_olsen_spot" )
	Sleep( 40 )
	if m01_state ~= "rescue" then
		M01_TestFail( "Olsen was freed while his guards could still fight" )
		return
	end
	SS2_Log( "TEST step: guards alive, Olsen still held" )

	for i = 0, GroupGetSize( houseGuards ) - 1 do
		UnitKill( GroupGetUnit( houseGuards, i ) )
	end
	Sleep( 40 )
	if m01_state ~= "extract" then
		M01_TestFail( "Olsen was not freed after his guards died, state "..m01_state )
		return
	end
	SS2_Log( "TEST step: Olsen freed" )

	-- Olsen now belongs to the player, so the party is five strong.
	party = PlayerGetUnits( 0 )
	if GroupGetSize( party ) ~= 5 then
		M01_TestFail( "Olsen did not join the team" )
		return
	end
	if m01_state == "done" then
		M01_TestFail( "mission completed before anyone reached the tree line" )
		return
	end
	for i = 0, GroupGetSize( party ) - 1 do
		UnitSetToWaypoint( GroupGetUnit( party, i ), "m01_extract" )
	end
	Sleep( 40 )
	if m01_state ~= "done" then
		M01_TestFail( "mission did not complete at the tree line, state "..m01_state )
		return
	end
	SS2_Log( "TEST PASS" )
end

StartThread( M01_Test )
