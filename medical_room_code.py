import glfw
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import numpy as np
from PIL import Image
import math
import time
import pygame
import pyassimp
from pygltflib import GLTF2, BufferFormat
from vbo_utils import crear_vbo, dibujar_vbo

is_jumping = False
is_crouching = False
vertical_velocity = 0.0
gravity = -0.001
jump_strength = 0.07
crouch_height = 0.001  
crouch_speed = 0.01 

door_angle = 0.0
door_opening = False
door_speed = 90.0 
last_time = time.time()

yaw = -90.0  
pitch = 0.0  
lastX = 400   
lastY = 300
first_mouse = True
speed = 0.2
sensitivity = 0.1

limits = {
    "min_x": -15.5,
    "max_x": 15.5,
    "min_z": -15.8,
    "max_z": 15.2,
    "min_y": 0.0,
    "max_y": 30.0
    }

collision_boxes = [
    [-3.5, -2.0, -4.5, 3.5, 3.0, -4.5],
    [-3.5, -2.0, -4.5, -3.5, 3.0, 6.0],  
    [3.5, -2.0, -4.5, 3.5, 3.0, 6.0], 
    [-3.5, -2.0, 6.0, -0.8, 3.0, 6.05], 
    [0.8, -2.0, 6.0, 3.5, 3.0, 6.05], 
    [-0.8, -2.0, 5.95, 0.8, 3.0, 6.05],
    [-13.3, -2.0, -13.3, -8.7, 9.5, -8.7],
    [8.7, -2.0, -13.3, 13.3, 9.5, -8.7],
    [-3.5, 3.0, -4.5, 3.5, 8.0, -4.5],
    [-3.5, 3.0, -4.5, -3.5, 8.0, -3.5],  
    [-3.5, 5.0, -3.5, -3.5, 8.0, -2.5], 
    [-3.5, 3.0, -2.5, -3.5, 8.0, 1.5], 
    [3.5, 3.0, -4.5, 3.5, 8.0, 1.5],
    [-3.5, 3.0, 6.0, -2.5, 3.8, 6.0], 
    [2.5, 3.0, 6.0, 3.5, 3.8, 6.0], 
    [-2.5, 3.0, 6.0, 2.5, 3.8, 6.0], 
]

def empty_box(box):
    return all(coordination == 0 for coordination in box)

def window_start(tittle="OpenGL Project - Medical Room"):
    width, high = 1200, 900  #Tamaño fijo
    if not glfw.init():
        raise Exception("we can not start glfw")

    window = glfw.create_window(width, high, tittle, None, None)

    if not window:
        glfw.terminate()
        raise Exception("can not create the window")

    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST)
    
    glfw.set_cursor_pos_callback(window, mouse_callback)
    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

    return window

def collision_things(new_pos, limits):
    global is_jumping, vertical_velocity, in_stairs, in_second_floor

    player_radius = 0.1
    player_height = normal_height if not is_crouching else crouch_height

    player_min = np.array([new_pos[0] - player_radius, new_pos[1], new_pos[2] - player_radius])
    player_max = np.array([new_pos[0] + player_radius, new_pos[1] + player_height, new_pos[2] + player_radius])

    objet_collision = False
    floor_collision = False
    in_stairs = False
    in_second_floor = new_pos[1] > 3.0

    for i, stair in enumerate(colliders_stairs):
        if (player_max[0] > stair[0] and player_min[0] < stair[1] and
            player_max[2] > stair[4] and player_min[2] < stair[5]):

            if player_min[1] <= stair[3] + 1.5:
                in_stairs = True
                target_y = stair[3] if i < len(colliders_stairs) - 1 else stair[3] + 0.2
                if new_pos[1] < target_y:
                    new_pos[1] = min(new_pos[1] + 0.1, target_y)
                    vertical_velocity = 0
                    is_jumping = False
                    floor_collision = True

                if i < len(colliders_stairs) - 2:
                    objet_collision = False
                break

    if not in_stairs:
        for box in collision_boxes:
            if empty_box(box):
                continue
            box_min = np.array(box[:3])
            box_max = np.array(box[3:])

            if (player_max[0] > box_min[0] and player_min[0] < box_max[0] and
                player_max[2] > box_min[2] and player_min[2] < box_max[2] and
                player_max[1] > box_min[1] and player_min[1] < box_max[1]):

                if in_second_floor:
                    if (-3.6 <= new_pos[0] <= -3.4 and -3.5 <= new_pos[2] <= -2.5 and new_pos[1] < 5.0):
                        continue
                    if (-2.6 <= new_pos[0] <= 2.6 and 1.4 <= new_pos[2] <= 6.1):
                        continue

                if box_max[1] <= new_pos[1] + (0.6 if in_second_floor else 0.15):
                    new_pos[1] = box_max[1]
                    vertical_velocity = 0
                    is_jumping = False
                    floor_collision = True
                else:
                    objet_collision = True

    margen = player_radius * 1.5
    if in_second_floor:
        if (new_pos[0] < -3.5 + margen or new_pos[0] > 3.5 - margen or
            new_pos[2] < -4.5 + margen or new_pos[2] > 6.0 - margen):
            return camera_pos.copy()
    else:
        if (new_pos[0] < limits["min_x"] + margen or new_pos[0] > limits["max_x"] - margen or
            new_pos[2] < limits["min_z"] + margen or new_pos[2] > limits["max_z"] - margen):
            play_effect_sound('C:\\medical-room-repo\\Medical-rom\\sounds_effects\\hit.mp3')
            return camera_pos.copy()

    if new_pos[1] > limits["max_y"]:
        return camera_pos.copy()

    if objet_collision and not in_stairs:
        return camera_pos.copy()

    return new_pos

def process_input(window):
    global camera_pos, camera_front, camera_up, is_jumping, vertical_velocity
    global is_crouching, prev_time, door_opening, in_stairs
    global door_key_pressed, accumulated_move

    if 'door_key_pressed' not in globals():
        door_key_pressed = False
    if 'accumulated_move' not in globals():
        accumulated_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    current_time = glfw.get_time()
    delta_time = current_time - prev_time
    prev_time = current_time

    move_speed = 0.2 * delta_time * 60  
    jump_speed = 0.3 * delta_time * 60
    smooth_factor = 20.0 * delta_time 

    horizontal_front = np.array([camera_front[0], 0.0, camera_front[2]])
    if np.linalg.norm(horizontal_front) > 0.0001:
        front_normalized = horizontal_front / np.linalg.norm(horizontal_front)
    else:
        front_normalized = np.array([0.0, 0.0, 0.0])
    
    right_normalized = np.cross(front_normalized, camera_up)
    if np.linalg.norm(right_normalized) > 0.0001:
        right_normalized = right_normalized / np.linalg.norm(right_normalized)

    target_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        target_move += front_normalized
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        target_move -= front_normalized
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        target_move -= right_normalized
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        target_move += right_normalized

    if np.linalg.norm(target_move) > 0:
        target_move = target_move / np.linalg.norm(target_move)

    accumulated_move = accumulated_move * (1.0 - smooth_factor) + target_move * smooth_factor

    if np.linalg.norm(accumulated_move) > 0.01:
        move_vector = accumulated_move * move_speed
        new_pos = camera_pos + move_vector
        new_pos[1] = camera_pos[1] 
        camera_pos = collision_things(new_pos, limits)

    if (glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and 
        not is_jumping and 
        not is_crouching and 
        not in_stairs and
        camera_pos[1] <= normal_height + 0.1):
        vertical_velocity = jump_speed
        is_jumping = True

    if glfw.get_key(window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS:
        if not is_jumping:  
            camera_pos[1] = crouch_height
            is_crouching = True
    else:
        if is_crouching:
            camera_pos[1] = normal_height
            is_crouching = False

    if glfw.get_key(window, glfw.KEY_F) == glfw.PRESS and not door_key_pressed:
        door_pos = np.array([0.0, 0.0, 6.0])
        if np.linalg.norm(camera_pos - door_pos) < 2.0:  
            door_opening = not door_opening
            door_key_pressed = True
    elif glfw.get_key(window, glfw.KEY_F) == glfw.RELEASE:
        door_key_pressed = False

    if in_stairs:
        vertical_move = 0.0
        if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
            vertical_move += move_speed * 0.5 
        if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
            vertical_move -= move_speed * 0.5 
        
        if vertical_move != 0.0:
            new_pos = camera_pos.copy()
            new_pos[1] += vertical_move
            camera_pos = collision_things(new_pos, limits)
 
def gravity_apply():
    global vertical_velocity, is_jumping, in_stairs

    if in_stairs:
        vertical_velocity = 0
        is_jumping = False
        return

    if (is_jumping or camera_pos[1] > normal_height) and not is_crouching:
        vertical_velocity += gravity
        camera_pos[1] += vertical_velocity

    if camera_pos[1] < normal_height and not is_crouching:
        camera_pos[1] = normal_height
        vertical_velocity = 0.0
        is_jumping = False

def mouse_callback(window, xpos, ypos):
    global yaw, pitch, lastX, lastY, first_mouse, camera_front

    if first_mouse:
        lastX = xpos
        lastY = ypos
        first_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos
    lastX = xpos
    lastY = ypos

    xoffset *= sensitivity
    yoffset *= sensitivity

    yaw += xoffset
    pitch += yoffset

    pitch = max(-89.9, min(89.9, pitch))

    front = np.array([
        math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)),
        math.sin(math.radians(pitch)),
        math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
    ], dtype=np.float32)
    camera_front[:] = front / np.linalg.norm(front)

def texture_load(path):
    try:
        # Abrir la imagen y voltearla
        with Image.open(path) as img:
            # Convertir a RGBA si es necesario (soporta transparencia)
            if img.mode == 'P':
                img = img.convert('RGBA')
            elif img.mode == 'RGB':
                pass  # Ya está en formato correcto
            else:
                img = img.convert('RGB')
            
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            width, height = img.size

            # Determinar el formato OpenGL según los canales
            if img.mode == 'RGBA':
                format = GL_RGBA
                img_data = img.tobytes("raw", "RGBA", 0, -1)
            else:
                format = GL_RGB
                img_data = img.tobytes("raw", "RGB", 0, -1)

        # Generar y configurar la textura
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        
        glTexImage2D(GL_TEXTURE_2D, 0, format, width, height, 
                    0, format, GL_UNSIGNED_BYTE, img_data)
        
        # Configuración de parámetros de textura
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        
        # Generar mipmaps automáticamente
        glGenerateMipmap(GL_TEXTURE_2D)
        
        return texture

    except Exception as e:
        print(f"Error loading texture {path}: {str(e)}")
        return None

def draw_yard():
    glEnable(GL_TEXTURE_2D)

    glBindTexture(GL_TEXTURE_2D, texture_yard)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.5, -2.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.5, -2.0, 6.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -4.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(15.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(15.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, 6.0)   
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -15.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(15.5, -2.0, -15.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(15.5, -2.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -15.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, -15.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.5, -2.0, -15.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, -15.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.5, -2.0, -4.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, 6.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(15.5, -2.0, 6.0)   
    glTexCoord2f(1.0, 1.0); glVertex3f(15.5, -2.0, 15.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, 15.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, 6.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 15.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, 15.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.5, -2.0, 6.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 15.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.5, -2.0, 15.5)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)

def draw_stairs():
    global colliders_stairs

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_wood)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])

    widht_stairs = 1.5
    num_stairs = 30
    total_high = 5.0
    stair_high = total_high / num_stairs
    stair_deep = 0.25

    x_near = -3.5
    x_far = x_near - widht_stairs
    z_star = 5.5

    colliders_stairs = []

    glColor3f(0.85, 0.85, 0.85)
    for i in range(num_stairs):
        y_base = -2.0 + i * stair_high
        z_pos = z_star - i * stair_deep

        colliders_stairs.append((
            x_far - 0.1, x_near + 0.1,
            y_base - 0.05, y_base + 0.15,
            z_pos - stair_deep - 0.1, z_pos + 0.1
        ))

        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex3f(x_near, y_base, z_pos)
        glTexCoord2f(1,0); glVertex3f(x_near, y_base, z_pos - stair_deep)
        glTexCoord2f(1,1); glVertex3f(x_far, y_base, z_pos - stair_deep)
        glTexCoord2f(0,1); glVertex3f(x_far, y_base, z_pos)
        glEnd()

        if i < num_stairs * 0.7:
            colliders_stairs.append((
                x_far - 0.1, x_near + 0.1,
                y_base, y_base + stair_high,
                z_pos - stair_deep - 0.05, z_pos - stair_deep + 0.05
            ))

        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex3f(x_near, y_base, z_pos - stair_deep)
        glTexCoord2f(1,0); glVertex3f(x_near, y_base + stair_high, z_pos - stair_deep)
        glTexCoord2f(1,1); glVertex3f(x_far, y_base + stair_high, z_pos - stair_deep)
        glTexCoord2f(0,1); glVertex3f(x_far, y_base, z_pos - stair_deep)
        glEnd()

    platform = 2.5
    z_final_stairs = z_star - (num_stairs * stair_deep)
    y_final = -2.0 + num_stairs * stair_high

    colliders_stairs.append((
        x_far - 0.2, x_near + 0.2,
        y_final - 0.2, y_final + 0.3,
        z_final_stairs - platform - 0.2, z_final_stairs + 0.2
    ))

    glColor3f(0.9, 0.9, 0.9)
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex3f(x_near, y_final, z_final_stairs)
    glTexCoord2f(1,0); glVertex3f(x_near, y_final, z_final_stairs - platform)
    glTexCoord2f(1,1); glVertex3f(x_far, y_final, z_final_stairs - platform)
    glTexCoord2f(0,1); glVertex3f(x_far, y_final, z_final_stairs)
    glEnd()
  
def draw_skybox(camera_pos, camera_front, camera_up, texture_sky):
    glPushMatrix()
    
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_sky)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluPerspective(60, (1200/900), 0.1, 1000.0)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    target = camera_pos + camera_front
    gluLookAt(0, 0, 0,
              camera_front[0], camera_front[1], camera_front[2],  
              camera_up[0], camera_up[1], camera_up[2]) 
    
    glRotatef(90, 1, 0, 0)
    radio = 1000.0
    slices = 64
    stacks = 64
    
    quad = gluNewQuadric()
    gluQuadricTexture(quad, GL_TRUE)
    gluQuadricOrientation(quad, GLU_INSIDE)
    gluSphere(quad, radio, slices, stacks)
    gluDeleteQuadric(quad)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    
    glPopMatrix()

def draw_door():
    global door_angle, last_time, texture_door

    current_time = time.time()
    delta_time = current_time - last_time
    last_time = current_time

    open_door = [-0.8, -2.0, 5.95, 0.8, 3.0, 6.05]
    close_door = [0, 0, 0, 0, 0, 0]

    for i in range(len(collision_boxes)):
        if collision_boxes[i] == open_door or empty_box(collision_boxes[i]):
            collision_boxes[i] = close_door if door_angle >= 45 else open_door

    if door_opening:
        door_angle = min(door_angle + door_speed * delta_time, 90)
    else:
        door_angle = max(door_angle - door_speed * delta_time, 0)

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_door)
    glColor3f(1, 1, 1)

    glPushMatrix()
    glTranslatef(0.8, -2.0, 6.01)
    glRotatef(-door_angle, 0, 1, 0)
    glTranslatef(-0.8, 0, 0)

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-0.8, 0.0, 0.0)
    glTexCoord2f(1.0, 0.0); glVertex3f( 0.8, 0.0, 0.0)
    glTexCoord2f(1.0, 1.0); glVertex3f( 0.8, 3.0, 0.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-0.8, 3.0, 0.0)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(1.0, 0.0); glVertex3f(-0.8, 0.0, -0.05)
    glTexCoord2f(0.0, 0.0); glVertex3f( 0.8, 0.0, -0.05)
    glTexCoord2f(0.0, 1.0); glVertex3f( 0.8, 3.0, -0.05)
    glTexCoord2f(1.0, 1.0); glVertex3f(-0.8, 3.0, -0.05)
    glEnd()

    glPopMatrix()
    glDisable(GL_TEXTURE_2D)
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_door)
    glColor3f(1, 1, 1)

    # Posición exacta (ajustada al hueco junto a las escaleras)
    door_x = -3.5       # Pared izquierda (x fijo)
    door_y = 3.0        # Altura base del segundo piso (y = 3.0 en tu código)
    door_z = -3.5        # Posición Z cerca de las escaleras (ajusté según tu room)
    door_width = 1.2    # Ancho de la puerta (puedes cambiarlo)
    door_height = 2.3   # Alto de la puerta

    glPushMatrix()
    glTranslatef(door_x, door_y, door_z)

    # Cara frontal (hacia el interior de la habitación)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(0.0, 0.0, 0.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(0.0, 0.0, door_width)  # Se extiende en Z
    glTexCoord2f(1.0, 1.0); glVertex3f(0.0, door_height, door_width)
    glTexCoord2f(0.0, 1.0); glVertex3f(0.0, door_height, 0.0)
    glEnd()

    # Cara trasera (hacia afuera, opcional)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-0.05, 0.0, 0.0)          # Pequeño desplazamiento en X
    glTexCoord2f(1.0, 0.0); glVertex3f(-0.05, 0.0, door_width)
    glTexCoord2f(1.0, 1.0); glVertex3f(-0.05, door_height, door_width)
    glTexCoord2f(0.0, 1.0); glVertex3f(-0.05, door_height, 0.0)
    glEnd()

    glPopMatrix()
    glDisable(GL_TEXTURE_2D)

def draw_room():
    widht_window = 2.0        
    high_window = 1.8         
    window_pos_y = 1.6        
    window_pos_z = 0.0        
    mark_window = 0.1 
    
    glDepthMask(GL_TRUE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
        
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 0.0, 1.0])
  
    glEnable(GL_TEXTURE_2D)
    
    glBindTexture(GL_TEXTURE_2D, texture_floor)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)   
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)   
    glEnd()

    glBindTexture(GL_TEXTURE_2D, texture_wall)
    glBegin(GL_QUADS)
    glColor3f(1.0, 1.0, 1.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, texture_wall)
    
    window_x = 3.5  
    window_z_start = window_pos_z - widht_window/2
    window_z_end = window_pos_z + widht_window/2
    window_y_start = -2.0 + window_pos_y  
    window_y_end = window_y_start + high_window
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(window_x, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(window_x, -2.0, 6.0)
    glTexCoord2f(1.0, 0.7); glVertex3f(window_x, window_y_start, 6.0)
    glTexCoord2f(0.0, 0.7); glVertex3f(window_x, window_y_start, -4.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.7); glVertex3f(window_x, window_y_start, -4.5)
    glTexCoord2f(0.33, 0.7); glVertex3f(window_x, window_y_start, window_z_start)
    glTexCoord2f(0.33, 0.3); glVertex3f(window_x, window_y_end, window_z_start)
    glTexCoord2f(0.0, 0.3); glVertex3f(window_x, window_y_end, -4.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.66, 0.7); glVertex3f(window_x, window_y_start, window_z_end)
    glTexCoord2f(1.0, 0.7); glVertex3f(window_x, window_y_start, 6.0)
    glTexCoord2f(1.0, 0.3); glVertex3f(window_x, window_y_end, 6.0)
    glTexCoord2f(0.66, 0.3); glVertex3f(window_x, window_y_end, window_z_end)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.3); glVertex3f(window_x, window_y_end, -4.5)
    glTexCoord2f(1.0, 0.3); glVertex3f(window_x, window_y_end, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(window_x, 3.0, 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(window_x, 3.0, -4.5)
    glEnd()
    
    glBindTexture(GL_TEXTURE_2D, texture_wood)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(window_x-mark_window, window_y_start, window_z_start)
    glTexCoord2f(1.0, 0.0); glVertex3f(window_x-mark_window, window_y_start, window_z_end)
    glTexCoord2f(1.0, 1.0); glVertex3f(window_x, window_y_start, window_z_end)
    glTexCoord2f(0.0, 1.0); glVertex3f(window_x, window_y_start, window_z_start)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(window_x-mark_window, window_y_end, window_z_start)
    glTexCoord2f(1.0, 0.0); glVertex3f(window_x-mark_window, window_y_end, window_z_end)
    glTexCoord2f(1.0, 1.0); glVertex3f(window_x, window_y_end, window_z_end)
    glTexCoord2f(0.0, 1.0); glVertex3f(window_x, window_y_end, window_z_start)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(window_x-mark_window, window_y_start, window_z_start)
    glTexCoord2f(1.0, 0.0); glVertex3f(window_x, window_y_start, window_z_start)
    glTexCoord2f(1.0, 1.0); glVertex3f(window_x, window_y_end, window_z_start)
    glTexCoord2f(0.0, 1.0); glVertex3f(window_x-mark_window, window_y_end, window_z_start)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(window_x-mark_window, window_y_start, window_z_end)
    glTexCoord2f(1.0, 0.0); glVertex3f(window_x, window_y_start, window_z_end)
    glTexCoord2f(1.0, 1.0); glVertex3f(window_x, window_y_end, window_z_end)
    glTexCoord2f(0.0, 1.0); glVertex3f(window_x-mark_window, window_y_end, window_z_end)
    glEnd()

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_wall)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)
    glTexCoord2f(0.2, 0.0); glVertex3f(-0.8, -2.0, 6.0)
    glTexCoord2f(0.2, 0.4); glVertex3f(-0.8, 1.0, 6.0)
    glTexCoord2f(0.0, 0.4); glVertex3f(-3.5, 1.0, 6.0)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.8, 0.0); glVertex3f(0.8, -2.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.4); glVertex3f(3.5, 1.0, 6.0)
    glTexCoord2f(0.8, 0.4); glVertex3f(0.8, 1.0, 6.0)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.4); glVertex3f(-3.5, 1.0, 6.0)
    glTexCoord2f(1.0, 0.4); glVertex3f(3.5, 1.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)
    glEnd()

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_wall)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, 8.0, -4.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-2.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-2.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, 1.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.5, 5.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-1.5, 5.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-1.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.5, 8.0, 1.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-1.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-1.5, 8.0, 1.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 8.0, -4.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -4.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, -3.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 8.0, -3.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -4.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 5.0, -3.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 5.0, -2.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 8.0, -2.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -3.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -2.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -2.5)
    glEnd()
    
    glBindTexture(GL_TEXTURE_2D, texture_roof)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-4.0, 8.0, -5.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(4.0, 8.0, -5.0) 
    glTexCoord2f(1.0, 1.0); glVertex3f(4.0, 8.0, 2.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-4.0, 8.0, 2.0)   
    glEnd()
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_roof) 

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-2.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.8, 6.0)
    
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.8, 1.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(2.5, 3.8, 6.0)
    
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, 3.8, 1.5)
    glEnd()

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.5, 3.8, 6.0)
    glEnd()
    
    glEnable(GL_TEXTURE_2D)
    
    draw_stairs()
    draw_door() 
    
def sound_start(sound_path):
    pygame.mixer.init()
    pygame.mixer.music.load(sound_path)
    pygame.mixer.music.set_volume(0.5)  

def play_ambient_sound(loop=True):
    pygame.mixer.music.play(-1 if loop else 0)
    
def play_effect_sound(sound_path):
    effect = pygame.mixer.Sound(sound_path)
    effect.set_volume(0.5)
    effect.play()

def vision_setting():
    glMatrixMode(GL_PROJECTION) 
    glLoadIdentity()  
    gluPerspective(60, 1200/900, 1.0, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    center = camera_pos + camera_front
    gluLookAt(*camera_pos, *center, *camera_up)

def load_models(path):
    import os
    gltf = GLTF2().load(path)
    base_dir = os.path.dirname(path)

    if gltf.buffers[0].uri:
        buffer_path = os.path.join(base_dir, gltf.buffers[0].uri)
        with open(buffer_path, "rb") as f:
            buffer_bytes = f.read()
    else:
        buffer_bytes = gltf.binary_blob()

    primitivas = []

    vertex_offset = 0

    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            accessor_pos = gltf.accessors[primitive.attributes.POSITION]
            accessor_indices = gltf.accessors[primitive.indices]

            bv_pos = gltf.bufferViews[accessor_pos.bufferView]
            pos_offset = (bv_pos.byteOffset or 0) + (accessor_pos.byteOffset or 0)
            pos_count = accessor_pos.count
            pos_data = buffer_bytes[pos_offset:pos_offset + pos_count * 12]
            vertices = np.frombuffer(pos_data, dtype=np.float32).reshape((pos_count, 3))

            bv_indices = gltf.bufferViews[accessor_indices.bufferView]
            idx_offset = (bv_indices.byteOffset or 0) + (accessor_indices.byteOffset or 0)
            idx_count = accessor_indices.count
            idx_component_type = accessor_indices.componentType

            if idx_component_type == 5123:
                idx_dtype = np.uint16
            elif idx_component_type == 5125:
                idx_dtype = np.uint32
            else:
                idx_dtype = np.uint8

            idx_data = buffer_bytes[idx_offset:idx_offset + idx_count * np.dtype(idx_dtype).itemsize]
            indices = np.frombuffer(idx_data, dtype=idx_dtype)
            #indices = indices + vertex_offset

            # UVs
            uv_accessor_index = getattr(primitive.attributes, "TEXCOORD_0", None)
            if uv_accessor_index is not None:
                accessor_uv = gltf.accessors[uv_accessor_index]
                bv_uv = gltf.bufferViews[accessor_uv.bufferView]
                uv_offset = (bv_uv.byteOffset or 0) + (accessor_uv.byteOffset or 0)
                uv_count = accessor_uv.count
                uv_data = buffer_bytes[uv_offset:uv_offset + uv_count * 8]
                uvs = np.frombuffer(uv_data, dtype=np.float32).reshape((uv_count, 2))
            else:
                uvs = np.zeros((vertices.shape[0], 2), dtype=np.float32)

            # Textura de la primitiva
            textura_path = None
            # Dentro de load_models(), en la parte donde procesas los materiales:
            if primitive.material is not None:
                material = gltf.materials[primitive.material]
                
                # Verifica si el material tiene propiedades PBR
                if hasattr(material, 'pbrMetallicRoughness') and material.pbrMetallicRoughness is not None:
                    if hasattr(material.pbrMetallicRoughness, 'baseColorTexture') and material.pbrMetallicRoughness.baseColorTexture is not None:
                        idx = material.pbrMetallicRoughness.baseColorTexture.index
                        img_idx = gltf.textures[idx].source
                        textura_path = gltf.images[img_idx].uri
                        textura_path = os.path.join(base_dir, textura_path)

            primitivas.append({
                "vertices": vertices,
                "indices": indices,
                "uvs": uvs,
                "textura_path": textura_path
            })
            #vertex_offset += vertices.shape[0]

    return primitivas

def draw_models(primitivas, position=(0, 0, 0), rotation=(0, 0, 0, 0), scale=(0, 0, 0), texturas={}):
    glPushMatrix()
    
    # Aplicar transformaciones en orden correcto: escala -> rotación -> traslación
    glTranslatef(*position)
    
    # Rotación (dos modos de uso)
    if len(rotation) == 4:
        # Modo ángulo-eje: (angle, x, y, z)
        glRotatef(rotation[0], rotation[1], rotation[2], rotation[3])
    else:
        # Modo Euler angles: (pitch, yaw, roll)
        if rotation[0] != 0: glRotatef(rotation[0], 1, 0, 0)  # Pitch (X)
        if rotation[1] != 0: glRotatef(rotation[1], 0, 1, 0)  # Yaw (Y)
        if rotation[2] != 0: glRotatef(rotation[2], 0, 0, 1)  # Roll (Z)
    
    # Escala (admite escalado no uniforme)
    if isinstance(scale, (int, float)):
        glScalef(scale, scale, scale)
    else:
        glScalef(*scale)
    
    # Dibujar cada primitiva
    for prim in primitivas:
        # Determinar tipo de índices
        index_type = GL_UNSIGNED_INT  # Valor por defecto
        if "index_dtype" in prim:
            if prim["index_dtype"] == np.uint16:
                index_type = GL_UNSIGNED_SHORT
            elif prim["index_dtype"] == np.uint8:
                index_type = GL_UNSIGNED_BYTE
        
        # Obtener textura
        textura_id = texturas.get(prim.get("textura_path", ""), 0)
        
        # Dibujar
        dibujar_vbo(
            prim["vbo_vertices"],
            prim["vbo_uvs"],
            prim["vbo_indices"],
            prim["num_indices"],
            textura_id,
            index_type
        )
    
    glPopMatrix()

def main():
    window = window_start()
    
    global texture_sky, texture_wood, texture_wall, texture_roof, texture_floor, texture_yard, texture_door
    global texture_tree, texture_leaf, prev_time, accumulated_move, texture_mark, camera_pos, camera_front, camera_up, normal_height
    global colliders_stairs, in_stairs, door_key_pressed
    door_key_pressed = False
    colliders_stairs = []
    in_stairs = False
    
    normal_height = 0.35
    camera_pos = np.array([0.0, normal_height, 8.0], dtype=np.float32)
    camera_front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    
    prev_time = glfw.get_time()
    accumulated_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    
    texture_wall = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\wall_texture.jpg')
    texture_roof = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\roof_texture.jpg')
    texture_floor = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\floor_texture.jpg')
    texture_yard = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\garden_texture.jpg')
    texture_door = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\door_texture.jpg')
    texture_sky = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\skybox.jpg')
    texture_wood = texture_load('C:\\Medical-room-repo\\Medical-rom\\textures\\wood_texture.png')
    
    air_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\air-conditioner\\scene.gltf")
    air_model_textures = {}
    for prim in air_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in air_model_textures:
            air_model_textures[textura_path] = texture_load(textura_path)

    tank_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\oxygen-tank\\scene.gltf")
    tank_model_textures = {}
    for prim in tank_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in tank_model_textures:
            tank_model_textures[textura_path] = texture_load(textura_path)

    chair_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\office-chair\\scene.gltf")
    chair_model_textures = {}
    for prim in chair_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in chair_model_textures:
            chair_model_textures[textura_path] = texture_load(textura_path)
    
    
    tree_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\minecraft_tree\\scene.gltf")
    tree_model_textures = {}
    for prim in tree_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in tree_model_textures:
            tree_model_textures[textura_path] = texture_load(textura_path)
    
    desk_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\pc-desk\\scene.gltf")
    desk_model_textures = {}
    for prim in desk_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in desk_model_textures:
            desk_model_textures[textura_path] = texture_load(textura_path)
            
    light_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\light-bulb\\scene.gltf")
    light_model_textures = {}
    for prim in light_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in light_model_textures:
            light_model_textures[textura_path] = texture_load(textura_path)
    
    
    cabinet_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\filing-cabinet\\scene.gltf")
    cabinet_model_textures = {}
    for prim in cabinet_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in cabinet_model_textures:
            cabinet_model_textures[textura_path] = texture_load(textura_path)
    
    skeleton_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\skeleton\\scene.gltf")
    skeleton_model_textures = {}
    for prim in skeleton_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in skeleton_model_textures:
            skeleton_model_textures[textura_path] = texture_load(textura_path)
    
    monitor_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\medical-monitor\\scene.gltf")
    monitor_model_textures = {}
    for prim in monitor_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in monitor_model_textures:
            monitor_model_textures[textura_path] = texture_load(textura_path)
    
    scale_model = load_models("C:\\medical-room-repo\\Medical-rom\\models\\weight-scale\\scene.gltf")
    scale_model_textures = {}
    for prim in scale_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in scale_model_textures:
            scale_model_textures[textura_path] = texture_load(textura_path)
    
    bed_model = load_models('C:\\medical-room-repo\\Medical-rom\\models\\hospital-bed\\scene.gltf')
    bed_model_textures = {}
    for prim in bed_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in bed_model_textures:
            bed_model_textures[textura_path] = texture_load(textura_path)
    
    wheel_model = load_models('C:\\medical-room-repo\\Medical-rom\\models\\wheel-chair\\scene.gltf')
    wheel_model_textures = {}
    for prim in wheel_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in wheel_model_textures:
            wheel_model_textures[textura_path] = texture_load(textura_path)

    machine_model = load_models('C:\\medical-room-repo\\Medical-rom\\models\\laboratory-machine\\scene.gltf')
    machine_model_textures = {}
    for prim in machine_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in machine_model_textures:
            machine_model_textures[textura_path] = texture_load(textura_path)

    sink_model = load_models('C:\\medical-room-repo\\Medical-rom\\models\\sink-cabinet\\scene.gltf')
    sink_model_textures = {}
    for prim in sink_model:
        if prim["uvs"].shape[0] == prim["vertices"].shape[0]:
            prim["uvs"] = prim["uvs"].copy()
            
        prim["vbo_vertices"], prim["vbo_uvs"], prim["vbo_indices"], prim["num_indices"], prim["index_dtype"] = crear_vbo(
            prim["vertices"].astype(np.float32),
            prim["uvs"].astype(np.float32),
            prim["indices"]
        )
        textura_path = prim["textura_path"]
        if textura_path and textura_path not in sink_model_textures:
            sink_model_textures[textura_path] = texture_load(textura_path)
            
    sound_start('C:\\medical-room-repo\\Medical-rom\\sounds_effects\\Minecraft.mp3')
    play_ambient_sound(loop=True)
    
    while not glfw.window_should_close(window):
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        gravity_apply() 
        vision_setting() 
        process_input(window)
        
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glDepthMask(GL_FALSE)
        draw_skybox(camera_pos, camera_front, camera_up, texture_sky)
        glDepthMask(GL_TRUE)
        
        draw_room()  
        draw_yard() 
        
        draw_models(bed_model, position=(1.6, -1, -3.4), rotation=(-90, 1, 0, 0), scale=(1, 1, 1), texturas=bed_model_textures)
        draw_models(desk_model, position=(-2.2, -1.5, 3.65), rotation=(-90, 1, 0, 0), scale=(1, 2, 1.8), texturas=desk_model_textures)
        draw_models(cabinet_model, position=(-2.85, -0.1, -3.5), rotation=(-90, 0, 0, 0), scale=(0.03, 0.03, 0.03), texturas=cabinet_model_textures)
        draw_models(wheel_model, position=(-2.7, -2, 0.2), rotation=(90, -1, 0, 0), scale=(0.017, 0.017, 0.017), texturas=wheel_model_textures)
        draw_models(light_model, position=(0, 3.1, 0), rotation=(90, -1, 0, 0), scale=(1.2, 1.2, 1.2), texturas=light_model_textures)
        draw_models(air_model, position=(0.2, 2.2, -4.6), rotation=(90, -1, 0, 0), scale=(3, 3, 3), texturas=air_model_textures)
        draw_models(scale_model, position=(-2.8, -2.0, -1.6), rotation=(90, 0, 0, 0), scale=(3, 3, 3), texturas=scale_model_textures)
        draw_models(monitor_model, position=(-1.3, -2, -3.4), rotation=(-90, 1, 0, 0), scale=(3, 3, 3), texturas=monitor_model_textures)
        draw_models(skeleton_model, position=(2.8, -2, 4.8), rotation=(90, 0, 0, 0), scale=(0.45, 0.45, 0.45), texturas=skeleton_model_textures)
        draw_models(tank_model, position=(3.2, -1.35, 5.7), rotation=(-90, 1, 0, 0), scale=(0.2, 0.2, 0.2), texturas=tank_model_textures)
        draw_models(tree_model, position=(-12.5, -13, -12.8), rotation=(-90, 1, 0, 0), scale=(18, 18, 18), texturas=tree_model_textures)
        draw_models(chair_model, position=(-2.6, -1, 4), rotation=(90, 0, 0, 0), scale=(1, 1, 1), texturas=chair_model_textures)
        draw_models(machine_model, position=(3, -2, 2.9), rotation=(90, 0, 0, 0), scale=(1, 1, 1), texturas=machine_model_textures)
        draw_models(sink_model, position=(-0.75, -2, 0.6), rotation=(90, 0, 0, 0), scale=(0.01, 0.01, 0.01), texturas=sink_model_textures)

        glfw.swap_buffers(window)  
        glfw.poll_events() 

    glfw.terminate()
    
main()