# Medical-rom
This project involves the creation of a 3D medical office using OpenGL. Essential elements such as walls, doors, furniture, and medical equipment will be modeled using geometric primitives and imported models. A first-person camera will be implemented to explore the environment, along with lighting and textures to enhance realism. Additionally, basic interaction will be added, such as door opening and collision detection. The goal is to develop an immersive and functional visual representation of a medical space by applying fundamental computer graphics techniques.

![image](https://github.com/user-attachments/assets/5e301d5b-a396-438c-b546-5925bb1b63f8)

![image](https://github.com/user-attachments/assets/1c841bae-7cce-4ed8-be1d-58b63666e43c)

# Features:
1-Complex Movement and Collision System:

    Implement a first-person movement system with gravity, jumping, and crouching.
    Includes movement limits on the stage and floor/obstacle detection
2-Loading and Rendering of 3D Models (GLTF):

    Complete system for loading GLTF models with textures, vertices, and UVs
    Support for multiple medical models (stretchers, wheelchairs, monitors, etc.)
3-Skybox and Advanced Texturing:

    Spherical skybox wrapping the scene
    Detailed texturing of walls, floors, ceilings, and exteriors
4-Integrated Audio System:

    Ambient music that plays on a loop
    Sound effects for interactions (like hits)
# Controls

- "W": go forward.
- "A": move to the left.
- "S": go backwards.
- "D": move to the right.
- "F": open the door when you're near.
- "SPACE": jump.
- "SHIFT": crouch
- "TOUCHPAD/MOUSE": move the camara

# How was it created?

A 3D simulator of a medical room was developed in Python using PyOpenGL and GLFW. It implements a first-person camera with WASD controls, jumping, and gravity. The 3D models (medical equipment) were loaded from GLTF files, with realistic textures and an accurate collision system. It includes interactions such as animated doors (F key) and sound effects with PyGame. To optimize performance, it uses VBOs and a spherical skybox. The code is organized into modular functions for better maintenance.

# Libraries of python to run the program:

- glfw - Window and input control management (keyboard/mouse)
- PyOpenGL - 3D rendering with OpenGL in Python
- numpy - Mathematical calculations and operations with matrices
- Pillow (PIL) - Image processing for textures
- pyassimp - Importing 3D models (GLTF/OBJ/FBX formats)
- pygltflib - Specific handling of GLTF/GLB files
- pygame - Audio system for effects and music

# How do you can install the libraries?

First, spilt your terminal in your development environment and then write this command and press ENTER:
    
    pip install glfw PyOpenGL numpy pillow pyassimp pygltflib pygame
    
![image](https://github.com/user-attachments/assets/9a4d0662-0dee-4e86-acb5-de9f97ea8029)

# Installation and Building:

1- Clone the repository:

    git clone https://github.com/yoelgod/Medical-rom.git
    cd Medical-rom

2- Install dependencies:

    pip install glfw PyOpenGL numpy pillow pyassimp pygltflib pygame

3- File structure

    Medical-rom/
    ├── models/          # Modelos 3D (GLTF)
    ├── textures/        # Texturas (.jpg, .png)
    ├── sounds_effects/  # Audios (.mp3)
    ├── medical_room_code.py          # Archivo principal
    └── vbo_utils.py

# Link of the video:

https://youtu.be/17p-DTjDJjo?si=bzu9ZOfOISOsxY0P

# Licence:

This project is licensed under the *MIT Lincese* – see the LICENSE file for details.

# Authors: 

- Soza Mendez Sergio Yamil https://github.com/ShamilUwunt
- Morales Velazques Diego Antonio https://github.com/DiegoMorales333
- Guevara Cajina Ervin Ulises https://github.com/SuperVinn
- Loasiga Garcia Christopher Yoel https://github.com/yoelgod
