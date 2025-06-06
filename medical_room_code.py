# pyright: ignore[reportMissingImports]
#Librería para crear la ventana y controlar eventos
import glfw
#Importa funciones de OpenGL
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
#Libreria de numpy facilita el manejo de arreglos y matrices, y se usa para definir las coordenadas de los vértices.
import numpy as np
from PIL import Image, ImageOps
import math
import time
import pygame

# Variables globales para física de movimiento
is_jumping = False
is_crouching = False
vertical_velocity = 0.0
gravity = -0.001
jump_strength = 0.07
normal_height = 0.35  # Altura normal (de pie)
crouch_height = 0.001  # Altura agachado
crouch_speed = 0.01    # Velocidad al agacharse/levantarse

# Variables globales para la animación de la puerta
door_angle = 0.0
door_opening = False
door_speed = 90.0  # grados por segundo
last_time = time.time()

#Variables globales para el movimiento de camara
camera_pos = np.array([0.0, normal_height, 8.0], dtype=np.float32) #Altura tipo "ojo humano"
camera_front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

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
    "max_y": 15.0 
}

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
    glEnable(GL_DEPTH_TEST)  #Habilitar la prueba de profundidad
    
    #Activar el callback del mouse y deshabilitar el cursor
    glfw.set_cursor_pos_callback(ventana, mouse_callback)
    glfw.set_input_mode(ventana, glfw.CURSOR, glfw.CURSOR_DISABLED)

    return ventana

#Funcion para validar colisiones mediante coordenadas
def actualizar_posicion_con_colision(nueva_pos, limites):
    colision = False
    colision_piso = False # Colisión con el piso
    if nueva_pos[0] < limites["min_x"]:
        nueva_pos[0] = limites["min_x"]
        colision = True
    elif nueva_pos[0] > limites["max_x"]:
        nueva_pos[0] = limites["max_x"]
        colision = True

    if nueva_pos[2] < limites["min_z"]:
        nueva_pos[2] = limites["min_z"]
        colision = True
    elif nueva_pos[2] > limites["max_z"]:
        nueva_pos[2] = limites["max_z"]
        colision = True

    if nueva_pos[1] < limites["min_y"]:
        nueva_pos[1] = limites["min_y"]
        colision = True
        colision_piso = True # Colisión con el piso
    elif nueva_pos[1] > limites["max_y"]:
        nueva_pos[1] = limites["max_y"]
        colision = True

    if colision and not colision_piso: # Si hay colisión pero no con el piso, reproducir sonido
        reproducir_efecto_sonido('C:\\medical-room-rep\\Medical-rom\\hit1.mp3')
    return nueva_pos

#Funcion para poder procesar las entradas atravez del teclado
def process_input(window):
    global camera_pos, is_jumping, vertical_velocity, is_crouching, prev_time, accumulated_move, door_opening
    
    current_time = glfw.get_time()
    delta_time = current_time - prev_time
    prev_time = current_time
    
    # Factor de suavizado (ajústalo según necesites)
    smooth_factor = 15.0 * delta_time
    
    # Configuración base
    camera_speed = speed
    target_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    
    # Calcular direcciones
    horizontal_front = np.array([camera_front[0], 0.0, camera_front[2]])
    if np.linalg.norm(horizontal_front) > 0.0001:
        front_normalized = horizontal_front / np.linalg.norm(horizontal_front)
    else:
        front_normalized = np.array([0.0, 0.0, 0.0])
    
    right_normalized = np.cross(front_normalized, camera_up)
    if np.linalg.norm(right_normalized) > 0.0001:
        right_normalized = right_normalized / np.linalg.norm(right_normalized)
    
    # Input processing
    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        target_move += front_normalized
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        target_move -= front_normalized
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        target_move -= right_normalized
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        target_move += right_normalized
    if glfw.get_key(window, glfw.KEY_F) == glfw.PRESS:  
        door_opening = not door_opening
    
    # Normalizar movimiento diagonal
    if np.linalg.norm(target_move) > 0:
        target_move = target_move / np.linalg.norm(target_move)
    
    # Suavizado del movimiento
    accumulated_move = accumulated_move * (1.0 - smooth_factor) + target_move * smooth_factor
    
    # Aplicar movimiento
    if np.linalg.norm(accumulated_move) > 0.01:
        move_vector = accumulated_move * camera_speed * delta_time * 60.0  # 60 FPS como referencia
        nueva_pos = camera_pos + move_vector
        nueva_pos[1] = camera_pos[1]
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)

    # Salto (solo si está en el suelo y no agachado)
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and not is_jumping and not is_crouching and camera_pos[1] <= normal_height + 0.1:
        vertical_velocity = jump_strength
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

#funcion para poder aplicar gravedad y no flotar    
def aplicar_gravedad():
    global camera_pos, vertical_velocity, is_jumping

    # Solo aplica gravedad si está en el aire y NO agachado
    if (is_jumping or camera_pos[1] > normal_height) and not is_crouching:
        vertical_velocity += gravity
        camera_pos[1] += vertical_velocity

    # Detección de suelo (si no está agachado)
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
    #Abrir imagen
    imagen = Image.open(ruta)
    imagen = imagen.transpose(Image.FLIP_TOP_BOTTOM)  #Voltear la imagen para OpenGL

    #Convertir la imagen a un formato adecuado para OpenGL
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
    # --- Pasto exterior ---
    # Parte izquierda
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

def dibujar_puerta():
    global door_angle, last_time, textura_puerta 
    
    # Calcular tiempo transcurrido
    current_time = time.time()
    delta_time = current_time - last_time
    last_time = current_time
    
    # Actualizar ángulo de la puerta (limitado a 90 grados para apertura interior)
    if door_opening:
        door_angle = min(door_angle + door_speed * delta_time, 90)
    else:
        door_angle = max(door_angle - door_speed * delta_time, 0)
    
    # Habilitar texturas
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_puerta)
    
    # Configurar propiedades de material
    glColor3f(1, 1, 1)  # Color blanco para que la textura se vea sin tintes
    
    # Dibujar la puerta
    glPushMatrix()
    # Posicionar el pivote en el borde derecho de la puerta
    glTranslatef(0.8, -2.0, 6.01)
    # Rotación (negativa para que abra hacia adentro)
    glRotatef(-door_angle, 0, 1, 0)
    # Compensación para dibujar en la posición correcta
    glTranslatef(-0.8, 0, 0)
    
    
    # Cara frontal de la puerta (con textura)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-0.8, 0.0, 0.0)   # Esquina inferior izquierda
    glTexCoord2f(1.0, 0.0); glVertex3f(0.8, 0.0, 0.0)    # Esquina inferior derecha
    glTexCoord2f(1.0, 1.0); glVertex3f(0.8, 3.0, 0.0)    # Esquina superior derecha
    glTexCoord2f(0.0, 1.0); glVertex3f(-0.8, 3.0, 0.0)   # Esquina superior izquierda
    glEnd()
    
    # Cara trasera (con textura invertida horizontalmente)
    glBegin(GL_QUADS)
    glTexCoord2f(1.0, 0.0); glVertex3f(-0.8, 0.0, -0.05)
    glTexCoord2f(0.0, 0.0); glVertex3f(0.8, 0.0, -0.05)
    glTexCoord2f(0.0, 1.0); glVertex3f(0.8, 3.0, -0.05)
    glTexCoord2f(1.0, 1.0); glVertex3f(-0.8, 3.0, -0.05)
    glEnd()
    
    glPopMatrix()
    
    # Deshabilitar texturas
    glDisable(GL_TEXTURE_2D)

def dibujar_cuarto():
    glEnable(GL_TEXTURE_2D)
    
    # --- Suelo (Z de -4.5 a 6.0) ---
    glBindTexture(GL_TEXTURE_2D, textura_suelo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)   
    glEnd()

    # --- Techo (profundidad reducida: Z de -4.5 a 6.0) ---
    glBindTexture(GL_TEXTURE_2D, textura_techo)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)  # Z cambiado de -5.5 a -4.5
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)    # Z cambiado de 7.0 a 6.0
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)   
    glEnd()
    
    # --- Pared trasera (Z = -4.5) ---
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)  # Z cambiado de -5.5 a -4.5
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, -4.5)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, -4.5)   
    glEnd()

    # --- Pared izquierda (Z de -4.5 a 6.0) ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, -4.5)  
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)   # Z cambiado de 7.0 a 6.0
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)    
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, -4.5)   
    glEnd()

    # --- Pared derecha (Z de -4.5 a 6.0) ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, -2.0, -4.5)   
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, 6.0)    
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)     
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, 3.0, -4.5)    
    glEnd()

    # --- Pared frontal con puerta (Z = 6.0) ---
       # --- Pared frontal con puerta (Z = 6.0) ---
    # Parte izquierda
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, -2.0, 6.0)
    glTexCoord2f(0.2, 0.0); glVertex3f(-0.8, -2.0, 6.0)   # Ancho aumentado de -0.6 a -0.8
    glTexCoord2f(0.2, 0.4); glVertex3f(-0.8, 1.0, 6.0)    # Mantenemos altura en 1.0
    glTexCoord2f(0.0, 0.4); glVertex3f(-3.5, 1.0, 6.0)
    glEnd()

    # Parte derecha
    glBegin(GL_QUADS)
    glTexCoord2f(0.8, 0.0); glVertex3f(0.8, -2.0, 6.0)    # Ancho aumentado de 0.6 a 0.8
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.4); glVertex3f(3.5, 1.0, 6.0)
    glTexCoord2f(0.8, 0.4); glVertex3f(0.8, 1.0, 6.0)
    glEnd()

    # Parte superior (sin cambios)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.4); glVertex3f(-3.5, 1.0, 6.0)
    glTexCoord2f(1.0, 0.4); glVertex3f(3.5, 1.0, 6.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)
    glEnd()

    glDisable(GL_TEXTURE_2D)

    # Dibujar la puerta (ahora con animación)
    dibujar_puerta()
    
def dibujar_arbol():
    # --- Arbol ---
    # Parte frontal
    glColor3f(0.5, 0.35, 0.05)  # Marron
    glBegin(GL_QUADS)
    glVertex3f(-10.0, 5.0, -10.5)
    glVertex3f(-12.0, 5.0, -10.5)
    glVertex3f(-12.0, -2.5, -10.5)
    glVertex3f(-10.0, -2.5, -10.5)
    glEnd()
    
    # Parte trasera
    glBegin(GL_QUADS)
    glVertex3f(-10, 5.0, -12.5)
    glVertex3f(-12.0, 5.0, -12.5)
    glVertex3f(-12.0, -2.5, -12.5)
    glVertex3f(-10.0, -2.5, -12.5)
    glEnd()
    
    # Parte izquierda
    glBegin(GL_QUADS)
    glVertex3f(-12.0, 5.0, -10.5)
    glVertex3f(-12.0, 5.0, -12.5)
    glVertex3f(-12.0, -2.5, -12.5)
    glVertex3f(-12.0, -2.5, -10.5)
    glEnd()
    
    # Parte derecha
    glBegin(GL_QUADS)
    glVertex3f(-10.0, 5.0, -10.5)
    glVertex3f(-10.0, 5.0, -12.5)
    glVertex3f(-10.0, -2.5, -12.5)
    glVertex3f(-10.0, -2.5, -10.5)
    glEnd()

    # --- Ojas ---
    # Parte frontal
    glColor3f(0.0, 0.6, 0.0)  # Verde
    glBegin(GL_QUADS)
    glVertex3f(-9.0, 7.0, -10.0)
    glVertex3f(-13.0, 7.0, -10.0)
    glVertex3f(-13.0, 4.5, -10.0)
    glVertex3f(-9.0, 4.5, -10.0)
    glEnd()
    
    # Parte trasera
    glBegin(GL_QUADS)
    glVertex3f(-9.0, 7.0, -13.0)
    glVertex3f(-13.0, 7.0, -13.0)
    glVertex3f(-13.0, 4.5, -13.0)
    glVertex3f(-9.0, 4.5, -13.0)
    glEnd()
    
    # Parte izquierda
    glBegin(GL_QUADS)
    glVertex3f(-13.0, 7.0, -10.0)
    glVertex3f(-13.0, 7.0, -13.0)
    glVertex3f(-13.0, 4.5, -13.0)
    glVertex3f(-13.0, 4.5, -10.0)
    glEnd()
    
    # Parte derecha
    glBegin(GL_QUADS)
    glVertex3f(-9.0, 7.0, -10.0)
    glVertex3f(-9.0, 7.0, -13.0)
    glVertex3f(-9.0, 4.5, -13.0)
    glVertex3f(-9.0, 4.5, -10.0)
    glEnd()
    

    glColor3f(1.0, 1.0, 1.0)  # Restaurar color blanco
    
# Función para inicializar el sonido
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
    # Definir la proyección en 3D (cámara ortogonal)
    glMatrixMode(GL_PROJECTION)  # Establecer modo de proyección
    glLoadIdentity()  # Limpiar la matriz de proyección
    gluPerspective(60, 1200/900, 1.0, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    center = camera_pos + camera_front
    gluLookAt(*camera_pos, *center, *camera_up)


# Función principal del programa
def main():
    ventana = inicializar_ventana()

    global textura_pared, textura_techo, textura_suelo, textura_pasto, textura_puerta, prev_time, accumulated_move
    
    prev_time = glfw.get_time()
    last_time = time.time()  # Inicializar tiempo para la puerta
    accumulated_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    
    textura_pared = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\wall_texture.jpg')
    textura_techo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\roof_texture.jpg')
    textura_suelo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\floor_texture.jpg')
    textura_pasto = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\garden_texture.jpg')
    textura_puerta = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\door_texture.jpg')
    
    # Inicializar sonido
    inicializar_sonido('C:\medical-room-rep\Medical-rom/Minecraft.mp3')
    reproducir_sonido_ambiente(loop=True)
    
    #Bucle principal
    while not glfw.window_should_close(ventana):
        
        #Limpiar tanto el buffer de color como el buffer de profundidad
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aplicar_gravedad() # Aplicar gravedad en cada frame
        configurar_vision()  #Configurar la visión para 3D
        process_input(ventana)
        dibujar_cuarto()  #Dibujar el cuarto
        dibujar_pasto() #Dibuja el pasto del cuadro
        dibujar_arbol()  #Dibujar el árbol

        
        #Intercambiar buffers y procesar eventos
        glfw.swap_buffers(ventana)  #Muestra lo que se ha dibujado
        glfw.poll_events()  #Captura eventos del teclado, mouse, etc.

    glfw.terminate()
    
main()