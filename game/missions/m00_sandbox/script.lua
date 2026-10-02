-- m00_sandbox: proves SS2 content loads and its script drives the mission.
-- Engine scripts are Lua 4.0: no booleans (nil is false), no "local function".

out( "SS2: m00_sandbox script running" )

raiders = GetGroup( SS2_GROUP_raiders )
out( "SS2: raiders placed: ", GroupGetSize( raiders ) )

DividedDeploy()
CameraSet( GetCamera( SS2_CAMERA_overview ) )
SetDiplomacy( 2, 0, DS_ENEMY )
SetDiplomacy( 0, 2, DS_ENEMY )

function WatchRaiders()
	while TRUE do
		Sleep( 20 )
		if not GroupCanFight( raiders ) then
			out( "SS2: all raiders are down" )
			return
		end
	end
end

function RaidersAdvance()
	Sleep( 40 )
	out( "SS2: raiders advance on the gate" )
	GroupMoveToWaypoint( raiders, "ss2_gate" )
end

StartThread( WatchRaiders )
StartThread( RaidersAdvance )
out( "SS2: m00_sandbox script started its threads" )
