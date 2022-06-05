# Procedural Mapping Tools
Procedural Mapping Tools is an experimental Houdini node library for mapping with Source Engine 1, Unreal Engine 1, and IdTech4.
It implements a set of nodes used to specify and export Source(.vmf), UE1(.t3d) and IdTech4(.map) level files.

# Requirements
PMT is designed to run on Windows 10 and Houdini 19.0 (Indie or NonCommercial). Python 3.7 is used by some setup scripts.

# Setup
The node library can be added to a Houdini project by importing the .hda files in pmt/hda.

Setup involves extracting and converting assets(models, materials, textures, sounds, class definitions) from the target engine to formats that can be read by Houdini.
The asset conversion process is fairly involved, with Source1 being the most complicated, IdTech4 of moderate difficulty and Unreal1 the easiest.

Full instructions are contained in the manual.

# License
PMT is generally licensed under a BSD style license; there are some components from the SideFX GameDev Toolkit licensed under MIT and a single node derived from GPLv2 licensed DarkRadiant.
See LICENSE for full details.