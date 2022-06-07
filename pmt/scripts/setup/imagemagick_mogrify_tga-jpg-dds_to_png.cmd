@echo off
rem Uses ImageMagick to convert .tga, .jpg, and .dds to .png
rem for using IdTech4 textures in PMT. 
rem 
rem Note that the /dds folder, if it exists, should be extracted into
rem /pmt/textures/map after running this script.
rem
rem This script should be run from C:\pmt\scripts\setup
rem 
set MOGRIFY_PATH=..\..\bin\ImageMagick-7.0.8-59-portable-Q16-x64\mogrify.exe
set SEARCH_PATH=..\..\textures\map

if not exist %MOGRIFY_PATH% (
	echo Could not find mogrify.exe at %MOGRIFY_PATH%
) else (
	cd %SEARCH_PATH%

	@echo on
	for /R %%f in (*.tga) do "%MOGRIFY_PATH%" -verbose -format png "%%f"
	for /R %%f in (*.jpg) do "%MOGRIFY_PATH%" -verbose -format png "%%f"
	for /R %%f in (*.dds) do "%MOGRIFY_PATH%" -verbose -format png "%%f"
)
pause