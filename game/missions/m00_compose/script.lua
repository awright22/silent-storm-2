-- m00_compose: checks that templates and objects added by SS2 appear in the level.
out( "SS2: m00_compose script running" )
DividedDeploy()
CameraSet( GetCamera( SS2_CAMERA_overview ) )
out( "SS2: guard valid: ", IsValid( GetUnit( "guard" ) ) )
