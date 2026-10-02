-- Scripted check of the composed test level, compiled in only by "build.py --test".
-- What a script can verify: who is on the map, that the added well exists as an
-- object, and that the guard walks his beat in both directions without a fight
-- starting. That the house and the sentry box are really there and look right
-- can only be judged from reviewed screenshots.

function Compose_TestFail( why )
	SS2_Log( "TEST FAIL: "..why )
end

function Compose_Test()
	local p, t
	for p = 0, 15 do
		local expected = 0
		if p == 0 then expected = 4 end
		if p == 1 then expected = 1 end
		local found = GroupGetSize( PlayerGetUnits( p ) )
		if found ~= expected then
			Compose_TestFail( "player slot "..p.." has "..found.." units, expected "..expected )
			return
		end
	end
	if not IsValid( GetObject( "ss2_well" ) ) then
		Compose_TestFail( "the well object is not on the map" )
		return
	end
	SS2_Log( "TEST step: four team members, one guard, the well" )

	-- The guard starts on patrol_a. Within a minute he must reach patrol_b and
	-- come back, and the neutral guard must not start a fight.
	local guard = GetUnit( "guard" )
	local reachedB = nil
	local returned = nil
	for t = 1, 60 do
		Sleep( 20 )
		if not IsRealTime() then
			Compose_TestFail( "a fight started although the guard is neutral, "..t.." s in" )
			return
		end
		if not reachedB then
			if SS2_DistanceTo( guard, "ss2_patrol_b" ) < 2 then
				reachedB = t
			end
		elseif SS2_DistanceTo( guard, "ss2_patrol_a" ) < 2 then
			returned = t
			break
		end
	end
	if not reachedB then
		Compose_TestFail( "the guard never reached the far end of his beat" )
		return
	end
	if not returned then
		Compose_TestFail( "the guard reached the far end after "..reachedB.." s but did not walk back" )
		return
	end
	SS2_Log( "TEST step: guard walked his beat out in "..reachedB.." s and was back after "..returned.." s" )
	SS2_Log( "TEST PASS" )
end

StartThread( Compose_Test )
