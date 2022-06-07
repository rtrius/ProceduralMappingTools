@echo off
rem Batchscript to export data for PMT
rem
rem This script exports Unreal Engine 1 textures, sounds, and class definitions to C:\pmt.
rem 
rem Copy this script to the root UE1 directory(containing /System/) before running it.
rem Tested with Unreal227i / UnrealTournament469b - other versions have issues with exporting.

set EXPORT_DIR=C:\pmt

@echo on
for /R %%F in (textures\*.utx) do mkdir %EXPORT_DIR%\textures\t3d\%%~nF\textures
for /R %%F in (textures\*.utx) do system\ucc.exe batchexport ..\textures\%%~nF.utx texture .bmp %EXPORT_DIR%\textures\t3d\%%~nF\textures

for /R %%F in (sounds\*.uax) do mkdir %EXPORT_DIR%\sounds\t3d\%%~nF\sounds
for /R %%F in (sounds\*.uax) do system\ucc.exe batchexport ..\sounds\%%~nF.uax sound .wav %EXPORT_DIR%\sounds\t3d\%%~nF\sounds

for /R %%F in (system\*.u) do mkdir %EXPORT_DIR%\classdefs\t3d\%%~nF\classes

rem UnrealIntegrity.u has issues with export, so exclude it
rem for /R %%F in (system\*.u) do system\ucc.exe batchexport ..\system\%%~nF.u class .uc %EXPORT_DIR%\classdefs\t3d\%%~nF\classes

for /R %%F in (system\*.u) do ( 
	if /i %%~nF == UnrealIntegrity (
		echo Skipping UnrealIntegrity.u...
	) else (
		system\ucc.exe batchexport ..\system\%%~nF.u class .uc %EXPORT_DIR%\classdefs\t3d\%%~nF\classes
	)
)
rem this does not work -- .t3d files exported do not contain mesh data
rem export mesh/lodmesh (vertex meshes)
rem for /R %%F in (system\*.u) do mkdir %EXPORT_DIR%\models\t3d\%%~nF\models
rem for /R %%F in (system\*.u) do system\ucc.exe batchexport ..\system\%%~nF.u mesh .t3d %EXPORT_DIR%\models\t3d\%%~nF\models

pause
