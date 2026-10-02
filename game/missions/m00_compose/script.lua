-- m00_compose: a level built from retail pieces, with a patrol and a dialogue.
-- Pipeline test, not part of the campaign.

SS2_Log( "m00_compose start" )

BeginSequence( 1 )
DividedDeploy()
CameraSet( GetCamera( SS2_CAMERA_clearing ) )
SS2_Say( SS2_DIALOG_intro )
CameraSet( GetCamera( SS2_CAMERA_team ) )
EndSequence()

SS2_Log( "m00_compose briefing over" )
