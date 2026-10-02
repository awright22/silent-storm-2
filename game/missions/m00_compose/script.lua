-- m00_compose: checks that templates, objects, a patrol route and a dialogue
-- added by SS2 all work in the level.
out( "SS2: m00_compose script running" )
DividedDeploy()
CameraSet( GetCamera( SS2_CAMERA_overview ) )
out( "SS2: guard valid: ", IsValid( GetUnit( "guard" ) ) )

function WatchGuard()
	local i
	for i = 1, 12 do
		Sleep( 40 )
		out( "SS2: guard to patrol_a ", GetDistance( GetPos( GetUnit( "guard" ) ), GetWaypointPos( "ss2_patrol_a" ) ),
			" to patrol_b ", GetDistance( GetPos( GetUnit( "guard" ) ), GetWaypointPos( "ss2_patrol_b" ) ) )
	end
end
StartThread( WatchGuard )

out( "SS2: dialogue starts" )
WaitForUI( DialogPlay( SS2_DIALOG_intro ) )
out( "SS2: dialogue finished" )
