#Librería para crear la ventana y controlar eventos
import glfw
#Importa funciones de OpenGL
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
#Libreria de numpy facilita el manejo de arreglos y matrices, y se usa para definir las coordenadas de los vértices.
import numpy as np
from PIL import Image
import math
import time
import pygame
import pyassimp

# Variables globales para física de movimiento
is_jumping = False
is_crouching = False
vertical_velocity = 0.0
gravity = -0.001
jump_strength = 0.07
crouch_height = 0.001  # Altura agachado
crouch_speed = 0.01    # Velocidad al agacharse/levantarse

# Variables globales para la animación de la puerta
door_angle = 0.0
door_opening = False
door_speed = 90.0  # grados por segundo
last_time = time.time()

yaw = -90.0   #Ángulo horizontal
pitch = 0.0   #Ángulo vertical
lastX = 400   #Última posición del mouse (centro ventana)
lastY = 300
first_mouse = True
speed = 0.2
sensitivity = 0.1

limites = {
    "min_x": -15.5,
    "max_x": 15.5,
    "min_z": -15.8,
    "max_z": 15.2,
    "min_y": 0.0,
    "max_y": 30.0
    }

collision_boxes = [
    # Pared trasera
    [-3.5, -2.0, -4.5, 3.5, 3.0, -4.5],

    [-3.5, -2.0, -4.5, -3.5, 3.0, 6.0],  # Pared izquierda
    [3.5, -2.0, -4.5, 3.5, 3.0, 6.0], 
    
    # Pared frontal (dividida en dos, dejando hueco para la puerta)
    [-3.5, -2.0, 6.0, -0.8, 3.0, 6.05],  # izquierda
    [0.8, -2.0, 6.0, 3.5, 3.0, 6.05],   # derecha

    # Puerta (inicialmente cerrada)
    [-0.8, -2.0, 5.95, 0.8, 3.0, 6.05],

    # Árboles
    [-13.3, -2.0, -13.3, -8.7, 9.5, -8.7],
    [8.7, -2.0, -13.3, 13.3, 9.5, -8.7]
]

def es_caja_vacia(box):
    return all(coordenada == 0 for coordenada in box)

#Función para inicializar la ventana con tamaño fijo
def inicializar_ventana(titulo="Proyecto OpenGL Paso 1"):
    ancho, alto = 1200, 900  #Tamaño fijo
    if not glfw.init():
        raise Exception("No se pudo inicializar GLFW")

    ventana = glfw.create_window(ancho, alto, titulo, None, None)

    if not ventana:
        glfw.terminate()
        raise Exception("No se pudo crear la ventana")

    #Establecer el contexto de OpenGL en la ventana actual
    glfw.make_context_current(ventana)
    glEnable(GL_DEPTH_TEST)
    
    #Activar el callback del mouse y deshabilitar el cursor
    glfw.set_cursor_pos_callback(ventana, mouse_callback)
    glfw.set_input_mode(ventana, glfw.CURSOR, glfw.CURSOR_DISABLED)

    return ventana

def actualizar_posicion_con_colision(nueva_pos, limites):
    global is_jumping, vertical_velocity, en_escalera

    player_radius = 0.3
    player_height = normal_height if not is_crouching else crouch_height

    player_min = np.array([nueva_pos[0] - player_radius, nueva_pos[1], nueva_pos[2] - player_radius])
    player_max = np.array([nueva_pos[0] + player_radius, nueva_pos[1] + player_height, nueva_pos[2] + player_radius])

    colision_objeto = False
    colision_suelo = False
    en_escalera = False

    # 1. Verificar escaleras primero
    for escalon in colliders_escaleras:
        if (player_max[0] > escalon[0] and player_min[0] < escalon[1] and
            player_max[2] > escalon[4] and player_min[2] < escalon[5]):
            
            # Estamos dentro del área XZ de la escalera
            if escalon[2] <= player_max[1] <= escalon[3] + 0.5:  # Margen superior
                en_escalera = True
                nueva_pos[1] = escalon[3]  # Ajustamos altura al escalón
                colision_suelo = True
                break

    # 2. Verificar otras colisiones solo si no estamos en escalera
    if not en_escalera:
        for box in collision_boxes:
            if es_caja_vacia(box):
                continue

            box_min, box_max = np.array(box[:3]), np.array(box[3:])

            if (player_max[0] > box_min[0] and player_min[0] < box_max[0] and
                player_max[1] > box_min[1] and player_min[1] < box_max[1] and
                player_max[2] > box_min[2] and player_min[2] < box_max[2]):

                if box_max[1] <= nueva_pos[1] + 0.1:  # Colisión con el suelo
                    colision_suelo = True
                else:  # Colisión con pared/objeto
                    colision_objeto = True

    # 3. Verificar límites del mundo
    fuera_del_pasto = (
        nueva_pos[0] < limites["min_x"] or nueva_pos[0] > limites["max_x"] or
        nueva_pos[2] < limites["min_z"] or nueva_pos[2] > limites["max_z"] or
        nueva_pos[1] > limites["max_y"]
    )

    if fuera_del_pasto:
        reproducir_efecto_sonido('C:\\medical-room-repo\\Medical-rom\\hit1.mp3')
        return camera_pos.copy()

    if colision_objeto and not en_escalera:
        return camera_pos.copy()

    return nueva_pos

#Funcion para poder procesar las entradas atravez del teclado
def process_input(window):
    global camera_pos, camera_front, camera_up, is_jumping, vertical_velocity
    global is_crouching, prev_time, door_opening, en_escalera
    global door_key_pressed, accumulated_move

    # Inicialización segura
    if 'door_key_pressed' not in globals():
        door_key_pressed = False
    if 'accumulated_move' not in globals():
        accumulated_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    current_time = glfw.get_time()
    delta_time = current_time - prev_time
    prev_time = current_time

    # Configuración base
    move_speed = 0.2 * delta_time * 60  # Velocidad base ajustada a FPS
    jump_speed = 0.3 * delta_time * 60
    smooth_factor = 20.0 * delta_time  # Factor de suavizado

    # Calcular direcciones normalizadas
    horizontal_front = np.array([camera_front[0], 0.0, camera_front[2]])
    if np.linalg.norm(horizontal_front) > 0.0001:
        front_normalized = horizontal_front / np.linalg.norm(horizontal_front)
    else:
        front_normalized = np.array([0.0, 0.0, 0.0])
    
    right_normalized = np.cross(front_normalized, camera_up)
    if np.linalg.norm(right_normalized) > 0.0001:
        right_normalized = right_normalized / np.linalg.norm(right_normalized)

    # Procesamiento de input con suavizado
    target_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        target_move += front_normalized
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        target_move -= front_normalized
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        target_move -= right_normalized
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        target_move += right_normalized

    # Normalizar movimiento diagonal
    if np.linalg.norm(target_move) > 0:
        target_move = target_move / np.linalg.norm(target_move)

    # Suavizado del movimiento
    accumulated_move = accumulated_move * (1.0 - smooth_factor) + target_move * smooth_factor

    # Aplicar movimiento con colisiones
    if np.linalg.norm(accumulated_move) > 0.01:
        move_vector = accumulated_move * move_speed
        new_pos = camera_pos + move_vector
        new_pos[1] = camera_pos[1]  # Mantener altura actual
        camera_pos = actualizar_posicion_con_colision(new_pos, limites)

    # Salto (solo si está en el suelo y no agachado)
    if (glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and 
        not is_jumping and 
        not is_crouching and 
        not en_escalera and
        camera_pos[1] <= normal_height + 0.1):
        vertical_velocity = jump_speed
        is_jumping = True

    # Agacharse (Ctrl) - Cambio inmediato pero con límites
    if glfw.get_key(window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS:
        if not is_jumping:  # Solo permite agacharse en el suelo
            camera_pos[1] = crouch_height
            is_crouching = True
    else:
        if is_crouching:
            camera_pos[1] = normal_height
            is_crouching = False

    # Interacción con puertas (toggle con F)
    if glfw.get_key(window, glfw.KEY_F) == glfw.PRESS and not door_key_pressed:
        # Verificar si estamos cerca de la puerta
        door_pos = np.array([0.0, 0.0, 6.0])
        if np.linalg.norm(camera_pos - door_pos) < 2.0:  # Radio de 2 unidades
            door_opening = not door_opening
            door_key_pressed = True
    elif glfw.get_key(window, glfw.KEY_F) == glfw.RELEASE:
        door_key_pressed = False

    # Lógica especial para escaleras (solo movimiento vertical)
    if en_escalera:
        vertical_move = 0.0
        if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
            vertical_move += move_speed * 0.5  # Subir más lento
        if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
            vertical_move -= move_speed * 0.5  # Bajar más lento
        
        if vertical_move != 0.0:
            new_pos = camera_pos.copy()
            new_pos[1] += vertical_move
            camera_pos = actualizar_posicion_con_colision(new_pos, limites)

#funcion para poder aplicar gravedad y no flotar    
def aplicar_gravedad():
    global vertical_velocity, is_jumping, en_escalera

    # No aplicar gravedad si está en escalera
    if en_escalera:
        vertical_velocity = 0
        is_jumping = False
        return

    # Lógica normal de gravedad
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

#FUncion para poder ver la textura
def cargar_textura(ruta):
    imagen = Image.open(ruta)
    imagen = imagen.transpose(Image.FLIP_TOP_BOTTOM)  #Voltear la imagen para OpenGL

    ancho, alto = imagen.size
    imagen_data = imagen.tobytes("raw", "RGB", 0, -1)

    #Crear y activar la textura
    textura = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, textura)

    #Configuración de la textura
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, ancho, alto, 0, GL_RGB, GL_UNSIGNED_BYTE, imagen_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    return textura

def dibujar_pasto():
    glEnable(GL_TEXTURE_2D)

    glBindTexture(GL_TEXTURE_2D, textura_pasto)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.5, -2.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.5, -2.0, 6.0)
    glEnd()
    
    # Parte derecha
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -4.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(15.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(15.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, 6.0)   
    glEnd()
    
    # Partes del fondo (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -15.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(15.5, -2.0, -15.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(15.5, -2.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glEnd()
    
    # Partes del fondo (centro)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -15.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, -15.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glEnd()
    
    # Partes del fondo (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.5, -2.0, -15.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, -15.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.5, -2.0, -4.5)
    glEnd()
    
    # Partes del frente (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, 6.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(15.5, -2.0, 6.0)   
    glTexCoord2f(1.0, 1.0); glVertex3f(15.5, -2.0, 15.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, 15.5)
    glEnd()
    
    # Partes del frente (centro)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, 6.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 15.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, 15.5)
    glEnd()
    
    # Partes del frente (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.5, -2.0, 6.0)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)   
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 15.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.5, -2.0, 15.5)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)

def dibujar_escaleras():
    global colliders_escaleras
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_Madera)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    
    # Parámetros de las escaleras (ajustados a tus valores)
    ancho_escalera = 1.5
    num_escalones = 30
    altura_total = 5.0
    altura_escalon = altura_total / num_escalones
    profundidad_escalon = 0.25
    
    x_pegado = -3.5
    x_sobresale = x_pegado - ancho_escalera
    z_inicio = 5.5
    
    # Reiniciamos los colliders
    colliders_escaleras = []
    
    glColor3f(0.85, 0.85, 0.85)
    for i in range(num_escalones):
        y_base = -2.0 + i * altura_escalon
        z_pos = z_inicio - i * profundidad_escalon
        
        # Huella horizontal (colisión)
        colliders_escaleras.append((
            x_sobresale, x_pegado,        # X min, X max
            y_base, y_base + 0.05,        # Y min, Y max (muy fino para pisar)
            z_pos - profundidad_escalon, z_pos  # Z min, Z max
        ))
        
        # Dibujar huella
        glBegin(GL_QUADS)
        glVertex3f(x_pegado, y_base, z_pos)
        glVertex3f(x_pegado, y_base, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos)
        glEnd()
        
        # Contrahuella vertical (colisión)
        colliders_escaleras.append((
            x_sobresale, x_pegado,
            y_base, y_base + altura_escalon,
            z_pos - profundidad_escalon, z_pos - profundidad_escalon + 0.05
        ))
        
        # Dibujar contrahuella
        glBegin(GL_QUADS)
        glVertex3f(x_pegado, y_base, z_pos - profundidad_escalon)
        glVertex3f(x_pegado, y_base + altura_escalon, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base + altura_escalon, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos - profundidad_escalon)
        glEnd()
    
    # Plataforma superior (colisión)
    plataforma_retroceso = 2.5
    z_final_escaleras = z_inicio - (num_escalones * profundidad_escalon)
    y_final = -2.0 + num_escalones * altura_escalon
    
    colliders_escaleras.append((
        x_sobresale, x_pegado,
        y_final - 0.1, y_final + 0.1,
        z_final_escaleras - plataforma_retroceso, z_final_escaleras
    ))
    
    # Dibujar plataforma
    glColor3f(0.9, 0.9, 0.9)
    glBegin(GL_QUADS)
    glVertex3f(x_pegado, y_final, z_final_escaleras)
    glVertex3f(x_pegado, y_final, z_final_escaleras - plataforma_retroceso)
    glVertex3f(x_sobresale, y_final, z_final_escaleras - plataforma_retroceso)
    glVertex3f(x_sobresale, y_final, z_final_escaleras)
    glEnd()
    
def dibujar_esfera_skybox(camera_pos, camera_front, camera_up, textura_cielo):
    glPushMatrix()
    
    # Configuraciones iniciales
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_cielo)
    
    # Guardamos la matriz de proyección actual
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluPerspective(60, (1200/900), 0.1, 1000.0)
    
    # Configuración de la vista
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Orientamos el skybox según la dirección de la cámara
    # Calculamos el punto hacia donde mira la cámara
    target = camera_pos + camera_front
    gluLookAt(0, 0, 0,  # Posición ficticia (el skybox siempre está centrado)
              camera_front[0], camera_front[1], camera_front[2],  # Dirección de mirada
              camera_up[0], camera_up[1], camera_up[2])  # Vector arriba
    
    # Rotación para orientar correctamente la esfera (ajustar según tu textura)
    glRotatef(90, 1, 0, 0)
    
    # Parámetros del skybox
    radio = 1000.0
    slices = 64
    stacks = 64
    
    # Dibujamos la esfera
    quad = gluNewQuadric()
    gluQuadricTexture(quad, GL_TRUE)
    gluQuadricOrientation(quad, GLU_INSIDE)
    gluSphere(quad, radio, slices, stacks)
    gluDeleteQuadric(quad)
    
    # Restauramos las matrices
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    # Restauramos el estado de OpenGL
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    
    glPopMatrix()

def dibujar_puerta():  
    global door_angle, last_time, textura_puerta

    # Calcular tiempo transcurrido
    current_time = time.time()
    delta_time = current_time - last_time
    last_time = current_time

    # Cajas de colisión para la puerta
    puerta_cerrada = [-0.8, -2.0, 5.95, 0.8, 3.0, 6.05]
    puerta_abierta = [0, 0, 0, 0, 0, 0]

    # Actualizar la caja de colisión en la lista si existe
    for i in range(len(collision_boxes)):
        if collision_boxes[i] == puerta_cerrada or es_caja_vacia(collision_boxes[i]):
            collision_boxes[i] = puerta_abierta if door_angle >= 45 else puerta_cerrada

    # Actualizar ángulo de apertura
    if door_opening:
        door_angle = min(door_angle + door_speed * delta_time, 90)
    else:
        door_angle = max(door_angle - door_speed * delta_time, 0)

    # Dibujar puerta con textura
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_puerta)
    glColor3f(1, 1, 1)

    glPushMatrix()
    glTranslatef(0.8, -2.0, 6.01)
    glRotatef(-door_angle, 0, 1, 0)
    glTranslatef(-0.8, 0, 0)

    # Cara frontal
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-0.8, 0.0, 0.0)
    glTexCoord2f(1.0, 0.0); glVertex3f( 0.8, 0.0, 0.0)
    glTexCoord2f(1.0, 1.0); glVertex3f( 0.8, 3.0, 0.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-0.8, 3.0, 0.0)
    glEnd()

    # Cara trasera
    glBegin(GL_QUADS)
    glTexCoord2f(1.0, 0.0); glVertex3f(-0.8, 0.0, -0.05)
    glTexCoord2f(0.0, 0.0); glVertex3f( 0.8, 0.0, -0.05)
    glTexCoord2f(0.0, 1.0); glVertex3f( 0.8, 3.0, -0.05)
    glTexCoord2f(1.0, 1.0); glVertex3f(-0.8, 3.0, -0.05)
    glEnd()

    glPopMatrix()
    glDisable(GL_TEXTURE_2D)

def dibujar_cuarto():
    
    # Parámetros ajustables para la ventana (modifícalos según necesites)
    VENTANA_ANCHO = 2.0        # Ancho aumentado de la ventana
    VENTANA_ALTO = 1.8         # Alto aumentado de la ventana
    VENTANA_POS_Y = 1.6        # Posición vertical más alta (desde el suelo)
    VENTANA_POS_Z = 0.0        # Posición en profundidad (0 = centro)
    VENTANA_MARCO_GROSOR = 0.1 # Marco más grueso
    
    glDepthMask(GL_TRUE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
        
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 0.0, 1.0])
  
    glEnable(GL_TEXTURE_2D)
    
    # --- Suelo (Z de -4.5 a 6.0) ---
    glBindTexture(GL_TEXTURE_2D, textura_suelo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)   
    glEnd()
    
    # --- Techo ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)   
    glEnd()

    # --- Pared trasera ---
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    glBegin(GL_QUADS)
    glColor3f(1.0, 1.0, 1.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glEnd()

    # --- Pared izquierda ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glEnd()

    # --- Pared derecha CON VENTANA (más alta y sin vidrio) ---
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    
    # Calculamos las coordenadas de la ventana (más alta)
    ventana_x = 3.5  # Coordenada X de la pared derecha
    ventana_z_inicio = VENTANA_POS_Z - VENTANA_ANCHO/2
    ventana_z_fin = VENTANA_POS_Z + VENTANA_ANCHO/2
    ventana_y_inicio = -2.0 + VENTANA_POS_Y  # Más alta que antes
    ventana_y_fin = ventana_y_inicio + VENTANA_ALTO
    
    # Parte inferior de la ventana
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(ventana_x, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(ventana_x, -2.0, 6.0)
    glTexCoord2f(1.0, 0.7); glVertex3f(ventana_x, ventana_y_inicio, 6.0)
    glTexCoord2f(0.0, 0.7); glVertex3f(ventana_x, ventana_y_inicio, -4.5)
    glEnd()
    
    # Parte izquierda de la ventana
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.7); glVertex3f(ventana_x, ventana_y_inicio, -4.5)
    glTexCoord2f(0.33, 0.7); glVertex3f(ventana_x, ventana_y_inicio, ventana_z_inicio)
    glTexCoord2f(0.33, 0.3); glVertex3f(ventana_x, ventana_y_fin, ventana_z_inicio)
    glTexCoord2f(0.0, 0.3); glVertex3f(ventana_x, ventana_y_fin, -4.5)
    glEnd()
    
    # Parte derecha de la ventana
    glBegin(GL_QUADS)
    glTexCoord2f(0.66, 0.7); glVertex3f(ventana_x, ventana_y_inicio, ventana_z_fin)
    glTexCoord2f(1.0, 0.7); glVertex3f(ventana_x, ventana_y_inicio, 6.0)
    glTexCoord2f(1.0, 0.3); glVertex3f(ventana_x, ventana_y_fin, 6.0)
    glTexCoord2f(0.66, 0.3); glVertex3f(ventana_x, ventana_y_fin, ventana_z_fin)
    glEnd()
    
    # Parte superior de la ventana
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.3); glVertex3f(ventana_x, ventana_y_fin, -4.5)
    glTexCoord2f(1.0, 0.3); glVertex3f(ventana_x, ventana_y_fin, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(ventana_x, 3.0, 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(ventana_x, 3.0, -4.5)
    glEnd()
    
    # --- Marco de la ventana (más grueso) ---
    glBindTexture(GL_TEXTURE_2D, textura_marco)
    
    # Marco inferior
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_inicio, ventana_z_inicio)
    glTexCoord2f(1.0, 0.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_inicio, ventana_z_fin)
    glTexCoord2f(1.0, 1.0); glVertex3f(ventana_x, ventana_y_inicio, ventana_z_fin)
    glTexCoord2f(0.0, 1.0); glVertex3f(ventana_x, ventana_y_inicio, ventana_z_inicio)
    glEnd()
    
    # Marco superior
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_fin, ventana_z_inicio)
    glTexCoord2f(1.0, 0.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_fin, ventana_z_fin)
    glTexCoord2f(1.0, 1.0); glVertex3f(ventana_x, ventana_y_fin, ventana_z_fin)
    glTexCoord2f(0.0, 1.0); glVertex3f(ventana_x, ventana_y_fin, ventana_z_inicio)
    glEnd()
    
    # Marco izquierdo
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_inicio, ventana_z_inicio)
    glTexCoord2f(1.0, 0.0); glVertex3f(ventana_x, ventana_y_inicio, ventana_z_inicio)
    glTexCoord2f(1.0, 1.0); glVertex3f(ventana_x, ventana_y_fin, ventana_z_inicio)
    glTexCoord2f(0.0, 1.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_fin, ventana_z_inicio)
    glEnd()
    
    # Marco derecho
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_inicio, ventana_z_fin)
    glTexCoord2f(1.0, 0.0); glVertex3f(ventana_x, ventana_y_inicio, ventana_z_fin)
    glTexCoord2f(1.0, 1.0); glVertex3f(ventana_x, ventana_y_fin, ventana_z_fin)
    glTexCoord2f(0.0, 1.0); glVertex3f(ventana_x-VENTANA_MARCO_GROSOR, ventana_y_fin, ventana_z_fin)
    glEnd()

    # --- Resto del código original ---
    # [Aquí iría el resto de tu función sin cambios...]
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    # --- Pared frontal con puerta (Z = 6.0) ---
    # Parte izquierda
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)
    glTexCoord2f(0.2, 0.0); glVertex3f(-0.8, -2.0, 6.0)
    glTexCoord2f(0.2, 0.4); glVertex3f(-0.8, 1.0, 6.0)
    glTexCoord2f(0.0, 0.4); glVertex3f(-3.5, 1.0, 6.0)
    glEnd()

    # Parte derecha
    glBegin(GL_QUADS)
    glTexCoord2f(0.8, 0.0); glVertex3f(0.8, -2.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.4); glVertex3f(3.5, 1.0, 6.0)
    glTexCoord2f(0.8, 0.4); glVertex3f(0.8, 1.0, 6.0)
    glEnd()

    # Parte superior
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.4); glVertex3f(-3.5, 1.0, 6.0)
    glTexCoord2f(1.0, 0.4); glVertex3f(3.5, 1.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)
    glEnd()

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_pared)
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

    # Encima de la puerta
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.5, 5.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-1.5, 5.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-1.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.5, 8.0, 1.5)
    glEnd()

    # Derecha de la puerta (conectada a pared derecha en X=3.5)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-1.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-1.5, 8.0, 1.5)
    glEnd()

    # --- Pared trasera (ajustada a X=3.5) ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 8.0, -4.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -4.5)
    glEnd()

    # --- Pared izquierda COMPLETA (con marcos de puerta) ---
    # Tramo antes de la puerta trasera
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, -3.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 8.0, -3.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -4.5)
    glEnd()

    # Marco superior de la puerta trasera
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 5.0, -3.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 5.0, -2.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 8.0, -2.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -3.5)
    glEnd()

    # Tramo después de la puerta trasera
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -2.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 8.0, -2.5)
    glEnd()
    
        # ===== TECHO PLANO CON VOLADIZO REDUCIDO (0.5 unidades) =====
    glBindTexture(GL_TEXTURE_2D, textura_techo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-4.0, 8.0, -5.0)  # Esquina trasera izquierda (X: -3.5-0.5, Z: -4.5-0.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(4.0, 8.0, -5.0)   # Esquina trasera derecha (X: 3.5+0.5, Z: -4.5-0.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(4.0, 8.0, 2.0)    # Esquina frontal derecha (X: 3.5+0.5, Z: 1.5+0.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-4.0, 8.0, 2.0)   # Esquina frontal izquierda (X: -3.5-0.5, Z: 1.5+0.5)
    glEnd()
    
        # ===== BARANDAS FRONTALES CONECTADAS =====
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_techo)  # Usando textura de pared

    # --- Baranda izquierda (X=-3.5 a -2.5, Z=6.0) ---
    glBegin(GL_QUADS)
    # Segmento frontal (Z=6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-2.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.8, 6.0)
    
    # Segmento lateral (Z=1.5 a 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.8, 1.5)
    glEnd()

    # --- Baranda derecha (X=2.5 a 3.5, Z=6.0) ---
    glBegin(GL_QUADS)
    # Segmento frontal (Z=6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(2.5, 3.8, 6.0)
    
    # Segmento lateral (Z=1.5 a 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, 3.8, 1.5)
    glEnd()

    # --- Unión central (X=-2.5 a 2.5, Z=6.0) ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.5, 3.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.5, 3.8, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.5, 3.8, 6.0)
    glEnd()

    glEnable(GL_TEXTURE_2D)
    
    dibujar_escaleras()
    # Dibujar la puerta (ahora con animación)
    dibujar_puerta()
    
def dibujar_hojas_izquierdo():
    # --- Hojas ---
    # Parte frontal (abajo)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_hojas)
    
    # Parte frontal (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 4.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 4.5, -10.0)
    glEnd()
    
    # Parte trasera (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 4.5, -13.0)
    glEnd()
    
    # Parte izquierda (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-13.0, 4.5, -10.0)
    glEnd()
    
    # Parte derecha (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 4.5, -10.0)
    glEnd()
    
    # Parte inferior (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 4.5, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 4.5, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 4.5, -13.0)
    glEnd()

    # Parte frontal (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 9.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 9.5, -10.0)
    glEnd()
    
    # Parte trasera (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 9.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 9.5, -13.0)
    glEnd()
    
    # Parte izquierda (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 9.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-13.0, 9.5, -10.0)
    glEnd()
    
    # Parte derecha (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 9.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 9.5, -10.0)
    glEnd()
    
    # Parte frontal (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.0, 5.5, -10.0)
    glEnd()
    
    # Parte trasera (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.0, 5.5, -13.0)
    glEnd()
    
    # Parte izquierda (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-15.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-15.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.0, 5.5, -10.0)
    glEnd()
    
    # Parte derecha (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-13.0, 5.5, -10.0)
    glEnd()
    
    # Parte inferior (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-15.0, 5.5, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 5.5, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-15.0, 5.5, -13.0)
    glEnd()
    
    # Parte frontal (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-7.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-7.0, 5.5, -10.0)
    glEnd()
    
    # Parte trasera (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-7.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-7.0, 5.5, -13.0)
    glEnd()
    
    # Parte izquierda (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-7.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-7.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-7.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-7.0, 5.5, -10.0)
    glEnd()
    
    # Parte derecha (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -10.0)
    glEnd()
    
    # Parte inferior (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-7.0, 5.5, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 5.5, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-7.0, 5.5, -13.0)
    glEnd()
    
    # Parte frontal (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -8.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -8.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -8.0)
    glEnd()
    
    # Parte trasera (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -10.0)
    glEnd()
    
    # Parte izquierda (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-13.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-13.0, 5.5, -8.0)
    glEnd()
    
    # Parte derecha (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -8.0)
    glEnd()
    
    # Parte inferior (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 5.5, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 5.5, -8.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -10.0)
    glEnd()
    
    # Parte frontal (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -13.0)
    glEnd()
    
    # Parte trasera (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -15.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -15.0)
    glEnd()
    
    # Parte izquierda (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-13.0, 5.5, -13.0)
    glEnd()
    
    # Parte derecha (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-9.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-9.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -13.0)
    glEnd()
    
    # Parte inferior (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-9.0, 5.5, -15.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-13.0, 5.5, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-9.0, 5.5, -13.0)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    
def dibujar_arbol_izquierdo():
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_arbol)
    
    # --- Tronco del árbol ---
    # Parte frontal 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-10.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-12.0, 5.0, -10.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-12.0, -2.5, -10.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-10.0, -2.5, -10.5)
    glEnd()
    
    # Parte trasera 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-10.0, 5.0, -12.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-12.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-12.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-10.0, -2.5, -12.5)
    glEnd()
    
    # Parte izquierda 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-12.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-12.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-12.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-12.0, -2.5, -10.5)
    glEnd()
    
    # Parte derecha 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-10.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(-10.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-10.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(-10.0, -2.5, -10.5)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    dibujar_hojas_izquierdo()  # Llamar a la función para dibujar las hojas del árbol
    
def dibujar_hojas_derecho():
    # --- Hojas ---
    # Parte frontal (abajo)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_hojas)
    
    # Parte frontal (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 4.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 4.5, -10.0)
    glEnd()
    
    # Parte trasera (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 4.5, -13.0)
    glEnd()
    
    # Parte izquierda (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 4.5, -10.0)
    glEnd()
    
    # Parte derecha (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 4.5, -10.0)
    glEnd()
    
    # Parte inferior (abajo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 4.5, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 4.5, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 4.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 4.5, -13.0)
    glEnd()

    # Parte frontal (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 9.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 9.5, -10.0)
    glEnd()
    
    # Parte trasera (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 9.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 9.5, -13.0)
    glEnd()
    
    # Parte izquierda (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 9.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 9.5, -10.0)
    glEnd()
    
    # Parte derecha (arriba)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 7.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 7.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 9.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 9.5, -10.0)
    glEnd()
    
    # Parte frontal (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(15.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(15.0, 5.5, -10.0)
    glEnd()
    
    # Parte trasera (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(15.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(15.0, 5.5, -13.0)
    glEnd()
    
    # Parte izquierda (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(15.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(15.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(15.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(15.0, 5.5, -10.0)
    glEnd()
    
    # Parte derecha (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glEnd()
    
    # Parte inferior (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(15.0, 5.5, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(15.0, 5.5, -13.0)
    glEnd()
    
    # Parte frontal (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(7.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(7.0, 5.5, -10.0)
    glEnd()
    
    # Parte trasera (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(7.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(7.0, 5.5, -13.0)
    glEnd()
    
    # Parte izquierda (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(7.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(7.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(7.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(7.0, 5.5, -10.0)
    glEnd()
    
    # Parte derecha (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glEnd()
    
    # Parte inferior (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(7.0, 5.5, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 5.5, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(7.0, 5.5, -13.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -8.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -8.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -8.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 5.5, -8.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -8.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 5.5, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 5.5, -8.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -15.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -15.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 5.5, -15.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 5.5, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    
def dibujar_arbol_derecho():
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_arbol)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(10.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(12.0, 5.0, -10.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(12.0, -2.5, -10.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(10.0, -2.5, -10.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(10.0, 5.0, -12.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(12.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(12.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(10.0, -2.5, -12.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(12.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(12.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(12.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(12.0, -2.5, -10.5)
    glEnd()
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(10.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(10.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(10.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(10.0, -2.5, -10.5)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    dibujar_hojas_derecho()  # Llamar a la función para dibujar las hojas del árbol
    
def inicializar_sonido(ruta_sonido):
    pygame.mixer.init()
    pygame.mixer.music.load(ruta_sonido)
    pygame.mixer.music.set_volume(0.5)  # Volumen (0.0 a 1.0)

def reproducir_sonido_ambiente(loop=True):
    pygame.mixer.music.play(-1 if loop else 0)
    
def reproducir_efecto_sonido(ruta_sonido):
    efecto = pygame.mixer.Sound(ruta_sonido)
    efecto.set_volume(0.5)
    efecto.play()

# Función para configurar la vista y proyección 3D
def configurar_vision():
    glMatrixMode(GL_PROJECTION)  # Establecer modo de proyección
    glLoadIdentity()  # Limpiar la matriz de proyección
    gluPerspective(60, 1200/900, 1.0, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    center = camera_pos + camera_front
    gluLookAt(*camera_pos, *center, *camera_up)

def cargar_modelo(ruta_modelo):
    try:
        process_flags = (pyassimp.postprocess.aiProcess_Triangulate |
                        pyassimp.postprocess.aiProcess_GenNormals |
                        pyassimp.postprocess.aiProcess_CalcTangentSpace |
                        pyassimp.postprocess.aiProcess_JoinIdenticalVertices)

        with pyassimp.load(ruta_modelo, processing=process_flags) as scene:
            if not scene.meshes:
                raise ValueError("El modelo no contiene mallas válidas")

            modelos = []
            for mesh in scene.meshes:
                # Procesamiento de geometría
                vertices = np.array(mesh.vertices, dtype=np.float32)
                faces = np.array(mesh.faces, dtype=np.uint32).flatten()
                
                # Normales (generar si no existen)
                if hasattr(mesh, 'normals') and mesh.normals is not None and len(mesh.normals) == len(vertices):
                    normals = np.array(mesh.normals, dtype=np.float32)
                else:
                    normals = np.zeros_like(vertices)
                    for i in range(0, len(faces), 3):
                        v0, v1, v2 = vertices[faces[i]], vertices[faces[i+1]], vertices[faces[i+2]]
                        normal = np.cross(v1 - v0, v2 - v0)
                        norm = np.linalg.norm(normal)
                        if norm > 0:
                            normal /= norm
                        normals[faces[i]] = normals[faces[i+1]] = normals[faces[i+2]] = normal

                # Crear VAO
                vao = glGenVertexArrays(1)
                glBindVertexArray(vao)

                # Vértices
                vbo = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, vbo)
                glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
                glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
                glEnableVertexAttribArray(0)

                # Normales
                nbo = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, nbo)
                glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals, GL_STATIC_DRAW)
                glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
                glEnableVertexAttribArray(1)

                # Índices
                ebo = glGenBuffers(1)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
                glBufferData(GL_ELEMENT_ARRAY_BUFFER, faces.nbytes, faces, GL_STATIC_DRAW)

                glBindVertexArray(0)

                modelos.append({
                    'vao': vao,
                    'num_indices': len(faces),
                    'material': getattr(mesh, 'material', None)
                })

            return modelos

    except Exception as e:
        print(f"Error al cargar modelo estilo Blender: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def dibujar_modelo_loop(modelo, posicion=(0, 0, 0), rotacion=(0, 0, 0, 0), escala=(1, 1, 1)):
    if not modelo:
        return

    # Configuración de iluminación profesional
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)

    # Configuración de luces (similar a Blender)
    glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 5.0, 5.0, 1.0])  # Luz clave
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
    
    glLightfv(GL_LIGHT1, GL_POSITION, [-5.0, 5.0, -5.0, 1.0])  # Luz de relleno
    glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
    glLightfv(GL_LIGHT1, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])

    glPushMatrix()
    glTranslatef(*posicion)
    glRotatef(rotacion[0], rotacion[1], rotacion[2], rotacion[3])
    glScalef(*escala)

    for malla in modelo:
        # Configuración de material profesional
        material = malla.get('material')
        if material:
            # Material del modelo
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, material.properties.get('ambient', [0.2, 0.2, 0.2, 1.0]))
            glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, material.properties.get('diffuse', [0.8, 0.8, 0.8, 1.0]))
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, material.properties.get('specular', [0.5, 0.5, 0.5, 1.0]))
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, material.properties.get('shininess', 32.0))
        else:
            # Material por defecto (similar a Blender)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

        # Dibujado profesional
        glBindVertexArray(malla['vao'])
        glDrawElements(GL_TRIANGLES, malla['num_indices'], GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

    glPopMatrix()

    # Limpieza
    glDisable(GL_LIGHT0)
    glDisable(GL_LIGHT1)
    
# Función principal del programa
def main():
    ventana = inicializar_ventana()
    
    global textura_cielo, textura_Madera, textura_pared, textura_techo, textura_suelo, textura_pasto, textura_puerta
    global textura_arbol, textura_hojas, prev_time, accumulated_move, textura_marco, camera_pos, camera_front, camera_up, normal_height
    global colliders_escaleras, en_escalera, door_key_pressed
    door_key_pressed = False
    colliders_escaleras = []
    en_escalera = False
    
    normal_height = 0.35
    camera_pos = np.array([0.0, normal_height, 8.0], dtype=np.float32) #Altura tipo "ojo humano"
    camera_front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    
    prev_time = glfw.get_time()
    last_time = time.time()  # Inicializar tiempo para la puerta
    accumulated_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    
    textura_pared = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\wall_texture.jpg')
    textura_techo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\roof_texture.jpg')
    textura_suelo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\floor_texture.jpg')
    textura_pasto = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\garden_texture.jpg')
    textura_puerta = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\door_texture.jpg')
    textura_arbol = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\tree_texture.jpg')
    textura_hojas = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\leaves_texture.jpg')
    textura_cielo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\skybox.jpg')
    textura_Madera = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\textura_Madera.png')
    textura_marco = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\textura_Madera.png')
    
    modelo_cama = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\hospital-bed\\hospital-bed.obj")
    modelo_desk = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\pc-desk\\desk.obj")
    modelo_wheel = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\wheel-chair\\wheel-chair.obj")
    modelo_curtain = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\bed-curtain\\bed-curtain.obj")
    modelo_light = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\light-bulb\\light-bulb.obj")
    modelo_cabinet = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\filing-cabinet\\filing-cabinet.obj")
    modelo_chair = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\wooden-chair\\wooden-chair.obj")
    modelo_monitor = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\medical-monitor\\medical-monitor.obj")
    modelo_scale = cargar_modelo("C:\\medical-room-repo\\Medical-rom\\models\\weight-scale\\weight-scale.obj")
    
    inicializar_sonido('C:\\medical-room-repo\\Medical-rom\\Minecraft.mp3')
    reproducir_sonido_ambiente(loop=True)
    
    #Bucle principal
    while not glfw.window_should_close(ventana):
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aplicar_gravedad() # Aplicar gravedad en cada frame
        configurar_vision()  #Configurar la visión para 3D
        process_input(ventana)
        
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glDepthMask(GL_FALSE)
        dibujar_esfera_skybox(camera_pos, camera_front, camera_up, textura_cielo)
        glDepthMask(GL_TRUE)
        
        dibujar_cuarto()  #Dibujar el cuarto
        dibujar_pasto() #Dibuja el pasto del cuadro
        dibujar_arbol_izquierdo() #Dibujar el árbol en la parte izquierda
        dibujar_arbol_derecho() #Dibujar el árbol en la parte derecha
        
        dibujar_modelo_loop(modelo_cama, rotacion=(-90, 0, 1, 0), posicion=(-0.05, -2, -3), escala=(0.5, 0.5, 0.5))
        dibujar_modelo_loop(modelo_desk, rotacion=(-90, 0, 2.5, 0), posicion=(-2.2, -1.5, 4), escala=(1.6, 2.1, 1.1))
        dibujar_modelo_loop(modelo_wheel, rotacion=(-90, 0, 1, 0), posicion=(2.35, -2, 4.5), escala=(2, 1.7, 2))
        dibujar_modelo_loop(modelo_curtain, rotacion=(-90, 0, 0, 0), posicion=(-2.3, -2, -1.2), escala=(0.5, 0.5, 0.5))
        dibujar_modelo_loop(modelo_light, rotacion=(-90, 0, 0, 0), posicion=(0, 1.75, 0.5), escala=(1.8, 1.8, 1.8))
        dibujar_modelo_loop(modelo_cabinet, rotacion=(-90, 0, -1, 0), posicion=(-2.85, -0.85, 2), escala=(2, 2, 2))
        dibujar_modelo_loop(modelo_chair, rotacion=(-90, 0, -1, 0), posicion=(-2.9, -2, 4.2), escala=(1.7, 1.7, 1.7))
        dibujar_modelo_loop(modelo_monitor, rotacion=(-90, 0, 0, 0), posicion=(-2, -2, -1.95), escala=(0.7, 0.7, 0.7))
        dibujar_modelo_loop(modelo_scale, rotacion=(90, 0, 0, 0), posicion=(2.7, 0.29, 2.7), escala=(1.5, 1.5, 1.5))

        glfw.swap_buffers(ventana)  #Muestra lo que se ha dibujado
        glfw.poll_events()  #Captura eventos del teclado, mouse, etc.

    glfw.terminate()
    
main()