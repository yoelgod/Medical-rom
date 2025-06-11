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
   # Limites en X, Y y Z
    if nueva_pos[0] < limites["min_x"]:
        nueva_pos[0] = limites["min_x"]
    elif nueva_pos[0] > limites["max_x"]:
        nueva_pos[0] = limites["max_x"]
            
    if nueva_pos[2] < limites["min_z"]:
        nueva_pos[2] = limites["min_z"]
    elif nueva_pos[2] > limites["max_z"]:
        nueva_pos[2] = limites["max_z"]
            
    if nueva_pos[1] < limites["min_y"]:
        nueva_pos[1] = limites["min_y"]
    elif nueva_pos[1] > limites["max_y"]:
        nueva_pos[1] = limites["max_y"]
        
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

def dibujar_esfera_skybox(cam_pos, textura_cielo):
    glPushMatrix()
    glRotatef(90, 1, 0, 0)

    
    # Posicionar la esfera en la cámara para que parezca infinita
    glTranslatef(cam_pos[0], cam_pos[1], cam_pos[2])
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_cielo)
    
    
    # Desactiva el depth test para que la esfera no bloquee nada
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)  # Opcional, para que no se oscurezca
    
    quad = gluNewQuadric()
    gluQuadricTexture(quad, GL_TRUE)
    gluQuadricOrientation(quad, GLU_INSIDE)  # Miramos la textura desde dentro
    
    radio = 50
    slices = 40
    stacks = 40
    gluSphere(quad, radio, slices, stacks)
    
    gluDeleteQuadric(quad)
    
    # Reactivar estado
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

def dibujar_escaleras():
    glDisable(GL_TEXTURE_2D)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    
    
    # Parámetros ajustados
    ancho_escalera = 1.5
    altura_escalon = 0.18
    profundidad_escalon = 0.45
    num_escalones = 28  # Para Y=3.0 (-2.0 + 28*0.18 ≈ 3.0)
    
    # Posiciones clave INVERTIDAS
    x_pegado = -3.5       # Pared izquierda
    x_sobresale = -3.5 - ancho_escalera
    z_inicio = 5.0        # Escaleras COMIENZAN cerca de la pared frontal (antes 6.0)
    z_final_escalera = z_inicio - (num_escalones * 0.3)  # Terminan atrás (-3.4)
    z_final_pared = -4.5   # Pared trasera (plataforma llega hasta aquí)
    
    # Color escalones
    glColor3f(0.8, 0.8, 0.8)
    
    # --- ESCALERAS (subiendo hacia ATRÁS, alejándose de la puerta) ---
    for i in range(num_escalones):
        y_base = -2.0 + i * altura_escalon
        z_pos = z_inicio - i * 0.3  # Se aleja de la pared frontal
        
        # Superficie del escalón
        glBegin(GL_QUADS)
        glVertex3f(x_pegado, y_base, z_pos)
        glVertex3f(x_pegado, y_base, z_pos + profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos + profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos)
        glEnd()
        
        # Contrahuella
        if i < num_escalones - 1:
            glColor3f(0.6, 0.6, 0.6)
            glBegin(GL_QUADS)
            glVertex3f(x_pegado, y_base, z_pos + profundidad_escalon)
            glVertex3f(x_pegado, y_base + altura_escalon, z_pos + profundidad_escalon)
            glVertex3f(x_sobresale, y_base + altura_escalon, z_pos + profundidad_escalon)
            glVertex3f(x_sobresale, y_base, z_pos + profundidad_escalon)
            glEnd()
            glColor3f(0.8, 0.8, 0.8)
    
    # --- PLATAFORMA EN PARED TRASERA ---
    glBegin(GL_QUADS)
    glVertex3f(x_pegado, 3.0, z_final_pared)      # Inicio (pared trasera)
    glVertex3f(x_pegado, 3.0, z_final_escalera)   # Final (donde terminan escaleras)
    glVertex3f(x_sobresale, 3.0, z_final_escalera)
    glVertex3f(x_sobresale, 3.0, z_final_pared)
    glEnd()
    
    # Barandilla completa
    glColor3f(0.5, 0.35, 0.2)
    grosor_barandilla = 0.1
    altura_barandilla = 0.9
    
    # Postes en escalones
    for i in range(0, num_escalones, 3):
        y_pos = -2.0 + i * altura_escalon
        z_pos = z_inicio - i * 0.3
        glBegin(GL_QUADS)
        glVertex3f(x_sobresale, y_pos, z_pos)
        glVertex3f(x_sobresale - grosor_barandilla, y_pos, z_pos)
        glVertex3f(x_sobresale - grosor_barandilla, y_pos + altura_barandilla, z_pos)
        glVertex3f(x_sobresale, y_pos + altura_barandilla, z_pos)
        glEnd()
    
    # Barandilla continua
    glBegin(GL_QUAD_STRIP)
    # Parte de escaleras
    for i in range(num_escalones):
        y_pos = -2.0 + i * altura_escalon + altura_barandilla
        z_pos = z_inicio - i * 0.3
        glVertex3f(x_sobresale, y_pos, z_pos)
        glVertex3f(x_sobresale - grosor_barandilla, y_pos, z_pos)
    
    # Parte de plataforma (hacia atrás)
    glVertex3f(x_sobresale, 3.0 + altura_barandilla, z_final_escalera)
    glVertex3f(x_sobresale - grosor_barandilla, 3.0 + altura_barandilla, z_final_escalera)
    glVertex3f(x_sobresale, 3.0 + altura_barandilla, z_final_pared)
    glVertex3f(x_sobresale - grosor_barandilla, 3.0 + altura_barandilla, z_final_pared)
    glEnd()


def dibujar_cuarto():
    
    
    # --- Pasto exterior ---
    # Parte izquierda
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
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)  # Z cambiado de -5.5 a -4.5
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)   
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 3.0, 6.0)    # Z cambiado de 7.0 a 6.0
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, 3.0, 6.0)   
    glEnd()

    # --- Pared trasera ---
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    glBegin(GL_QUADS)
    glColor3f(1.0, 1.0, 1.0);
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)  # Esquina inferior izquierda
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, -4.5)   # Esquina inferior derecha
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, -4.5)    # Esquina superior derecha
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)   # Esquina superior izquierda
    glEnd()

    # --- Pared izquierda ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(-3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(-3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-3.5, 3.0, -4.5)
    glEnd()

    # --- Pared derecha ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, -2.0, -4.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, -2.0, 6.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 6.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
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

    # --- Puerta (Z = 6.01) ---
    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(-0.8, -2.0, 6.01)   # Ancho aumentado de -0.6 a -0.8
    glVertex3f(0.8, -2.0, 6.01)    # Ancho aumentado de 0.6 a 0.8
    glVertex3f(0.8, 1.0, 6.01)     # Altura se mantiene en 1.0
    glVertex3f(-0.8, 1.0, 6.01)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    
    
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
    
    
    # --- Paredes del segundo piso (más pequeño que el primero) ---
    
        # --- Dimensiones del segundo piso ---
    altura_piso = 3.0  # Altura del segundo piso (de 3.0 a 6.0)
    ancho_izq = -3.5   # Mismo ancho que la planta baja
    ancho_der = 3.5    # Mismo ancho que la planta baja
    z_frente = 2.0     # Pared frontal más atrás (antes 6.0)
    z_trasera = -4.5   # Pared trasera
    
    # Habilitar textura de paredes
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    
    # --- Pared derecha ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ancho_der, 3.0, z_trasera)
    glTexCoord2f(1.0, 0.0); glVertex3f(ancho_der, 3.0, z_frente)
    glTexCoord2f(1.0, 1.0); glVertex3f(ancho_der, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0); glVertex3f(ancho_der, 6.0, z_trasera)
    glEnd()
    
       # --- Pared frontal con hueco para una puerta ---
    # Tramo antes de la puerta (izquierda)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(ancho_izq, 3.0, z_frente)
    glTexCoord2f(1.0, 0.0)
    glVertex3f(ancho_izq + 1.0, 3.0, z_frente)
    glTexCoord2f(1.0, 1.0)
    glVertex3f(ancho_izq + 1.0, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_frente)
    glEnd()

    # Tramo encima de la puerta (de 5.0 a 6.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(ancho_izq + 1.0, 5.0, z_frente)
    glTexCoord2f(1.0, 0.0)
    glVertex3f(ancho_izq + 2.0, 5.0, z_frente)
    glTexCoord2f(1.0, 1.0)
    glVertex3f(ancho_izq + 2.0, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0)
    glVertex3f(ancho_izq + 1.0, 6.0, z_frente)
    glEnd()

    # Tramo después de la puerta (derecha)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(ancho_izq + 2.0, 3.0, z_frente)
    glTexCoord2f(1.0, 0.0)
    glVertex3f(ancho_der, 3.0, z_frente)
    glTexCoord2f(1.0, 1.0)
    glVertex3f(ancho_der, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0)
    glVertex3f(ancho_izq + 2.0, 6.0, z_frente)
    glEnd()

    
    # --- Pared trasera ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ancho_izq, 3.0, z_trasera)
    glTexCoord2f(1.0, 0.0); glVertex3f(ancho_der, 3.0, z_trasera)
    glTexCoord2f(1.0, 1.0); glVertex3f(ancho_der, 6.0, z_trasera)
    glTexCoord2f(0.0, 1.0); glVertex3f(ancho_izq, 6.0, z_trasera)
    glEnd()
    
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_pared)

# Tramo antes de la puerta (parte baja)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(ancho_izq, 3.0, z_trasera)

    glTexCoord2f(1.0, 0.0)
    glVertex3f(ancho_izq, 3.0, z_trasera + 1.0)

    glTexCoord2f(1.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_trasera + 1.0)

    glTexCoord2f(0.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_trasera)
    glEnd()

# Tramo encima de la puerta (de 5.0 a 6.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(ancho_izq, 5.0, z_trasera + 1.0)

    glTexCoord2f(1.0, 0.0)
    glVertex3f(ancho_izq, 5.0, z_trasera + 2.0)

    glTexCoord2f(1.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_trasera + 2.0)

    glTexCoord2f(0.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_trasera + 1.0)
    glEnd()

# Tramo después de la puerta
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(ancho_izq, 3.0, z_trasera + 2.0)

    glTexCoord2f(1.0, 0.0)
    glVertex3f(ancho_izq, 3.0, z_frente)

    glTexCoord2f(1.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_frente)

    glTexCoord2f(0.0, 1.0)
    glVertex3f(ancho_izq, 6.0, z_trasera + 2.0)
    glEnd()

    glDisable(GL_TEXTURE_2D)

    
    # --- Abertura para escaleras (ajustada para coincidir) ---
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(ancho_izq, 3.0, z_trasera + 1.0)  # Coordenadas Z iguales que la puerta
    glVertex3f(ancho_izq + 1.0, 3.0, z_trasera + 1.0)
    glVertex3f(ancho_izq + 1.0, 3.0, z_trasera + 2.0)
    glVertex3f(ancho_izq, 3.0, z_trasera + 2.0)
    glEnd()
    
    
    
    dibujar_escaleras()
    # Dibujar la puerta (ahora con animación)
    dibujar_puerta()
    

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

    global textura_cielo, textura_pared, textura_techo, textura_suelo, textura_pasto, textura_puerta, prev_time, accumulated_move, cam_pos
    
    
    prev_time = glfw.get_time()
    last_time = time.time()  # Inicializar tiempo para la puerta
    accumulated_move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    
    textura_pared = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\wall_texture.jpg')
    textura_techo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\roof_texture.jpg')
    textura_suelo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\floor_texture.jpg')
    textura_pasto = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\garden_texture.jpg')
    textura_puerta = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\door_texture.jpg')
    textura_cielo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\skybox.jpg')
    
    cam_pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    #Bucle principal
    while not glfw.window_should_close(ventana):
        
        #Limpiar tanto el buffer de color como el buffer de profundidad
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aplicar_gravedad() # Aplicar gravedad en cada frame
        configurar_vision()  #Configurar la visión para 3D
        process_input(ventana)
        
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glDepthMask(GL_FALSE)
        dibujar_esfera_skybox(cam_pos, textura_cielo)
       
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0])   # luz general más intensa
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])   # luz directa intensa
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 0.0, 1.0]) # posición de la luz

        
        dibujar_cuarto()  #Dibujar el cuarto
        dibujar_pasto() #Dibuja el pasto del cuadro
        
        

        
        #Intercambiar buffers y procesar eventos
        glfw.swap_buffers(ventana)  #Muestra lo que se ha dibujado
        glfw.poll_events()  #Captura eventos del teclado, mouse, etc.

    glfw.terminate()
    
main()