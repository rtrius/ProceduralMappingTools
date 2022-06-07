# Procedural Mapping Tools
Procedural Mapping Tools is an experimental Houdini node library for mapping with Source Engine 1, Unreal Engine 1, and IdTech4.
It implements a set of nodes used to specify and export Source(.vmf), UE1(.t3d) and IdTech4(.map) level files.

# Requirements
PMT is designed to run on Windows 10 and Houdini 19.0 (Indie or NonCommercial). Python 3.7 is used by some setup scripts.

# Setup
/pmt from this repository must be copied to C:/pmt. Additionally, /pmt from pmt_template.zip should also be extracted to C:/pmt.
The node library assumes that asset data is stored in C:/pmt, and that exports are written to C:/pmt/exports.

The node library can be added to a Houdini project by importing the .hda files in C:/pmt/hda.

Setup involves extracting and converting assets(models, materials, textures, sounds, class definitions) from the target engine to formats that can be read by Houdini.
The asset conversion process is fairly involved, with Source1 being the most complicated, IdTech4 of moderate difficulty and Unreal1 the easiest.

Full instructions are contained in the manual.

# License
PMT is generally licensed under a BSD style license; there are some components from the SideFX GameDev Toolkit licensed under MIT and a single node derived from GPLv2 licensed DarkRadiant.
See LICENSE for full details.

# Dependencies (all engines)
Dependencies are collected in /dependencies; they can also be found at the links below.

Python 3.7 - for asset conversion and setup scripts
https://www.python.org

Assimp 4.1.0 - for converting model data into .obj
https://github.com/assimp/assimp/releases/tag/v4.1.0
https://github.com/assimp/assimp/releases/download/v4.1.0/assimp-sdk-4.1.0-setup.exe

ImageMagick - for image analysis and comparison; also for converting IdTech4 textures(.dds) files to .png
http://www.imagemagick.org

# Dependencies (Source1 only)
Crowbar - for unpacking .vpk files and decompiling .mdl files.
https://steamcommunity.com/groups/CrowbarTool
https://github.com/ZeqMacaw/Crowbar/releases

vtfedit - for converting .vtf textures to .png.
https://web.archive.org/web/20170913055549/http://nemesis.thewavelength.net/index.php?c=238\#p238 

# Dependencies (IdTech4 only)
To preview .ogg sounds in the editor, install opencodecs\_0.85.17777.exe from
https://xiph.org/dshow/downloads/
