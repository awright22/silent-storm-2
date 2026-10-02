-- Mission 1, "Cold Welcome".
--
-- Flow: briefing -> free Olsen (no German left fighting in the house and a team
-- member next to him) -> Olsen joins the team -> everyone back to the tree line.
-- Fails if Olsen dies. The engine's own lose screen covers the team going down.

olsen = GetUnit( "m01_olsen" )
houseGuards = GetGroup( SS2_GROUP_house )
yardGuards = GetGroup( SS2_GROUP_yard )

M01_FREE_RADIUS = 4        -- tiles: how close a team member must come to Olsen
M01_EXTRACT_RADIUS = 6     -- tiles: how close to the extraction point everyone must be

m01_state = "rescue"       -- rescue -> extract -> done / failed

function M01_Fail()
	m01_state = "failed"
	SS2_Log( "m01 failed: Olsen is dead" )
	SS2_Say( SS2_DIALOG_olsen_dead )
end

-- Olsen can die at any point before the mission is over.
function M01_WatchOlsen()
	while m01_state == "rescue" or m01_state == "extract" do
		Sleep( 10 )
		if UnitIsDead( olsen ) then
			M01_Fail()
			return
		end
	end
end

function M01_Rescue()
	while m01_state == "rescue" do
		Sleep( 10 )
		if not GroupCanFight( houseGuards ) and SS2_PartyNear( olsen, M01_FREE_RADIUS ) then
			m01_state = "extract"
			SS2_Log( "m01 objective done: Olsen freed" )
			UnitSetPlayer( olsen, 0 )
			SS2_Say( SS2_DIALOG_freed )
		end
	end
end

function M01_Extract()
	while m01_state ~= "extract" do
		if m01_state == "failed" then
			return
		end
		Sleep( 10 )
	end
	while m01_state == "extract" do
		Sleep( 10 )
		if SS2_PartyAt( "m01_extract", M01_EXTRACT_RADIUS ) then
			m01_state = "done"
			SS2_Log( "m01 complete" )
			SS2_Say( SS2_DIALOG_done )
			if SS2_InCampaign() then
				ScenarioGiveClue( "SS2_M01_DONE", 1, 1 )
				ExitToChapter()
			end
		end
	end
end

SS2_Log( "m01 start" )

-- Briefing as a sequence: the AI ignores everyone and nothing can start a fight
-- until the player has read it.
BeginSequence( 1 )
DividedDeploy()
CameraSet( GetCamera( SS2_CAMERA_farm ) )
SS2_Say( SS2_DIALOG_intro )
CameraSet( GetCamera( SS2_CAMERA_arrival ) )
EndSequence()

StartThread( M01_WatchOlsen )
StartThread( M01_Rescue )
StartThread( M01_Extract )
SS2_Log( "m01 briefing over, objectives running" )
