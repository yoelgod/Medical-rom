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
    "max_y": 30.0
    }

#Funcion para validar colisiones mediante coordenadas
def actualizar_posicion_con_colision(nueva_pos, limites):
    # Copia la posición para no modificar la original directamente
    pos = np.copy(nueva_pos)
    
    # --- 1. Límites generales del mundo ---
    pos[0] = np.clip(pos[0], limites["min_x"], limites["max_x"])
    pos[1] = np.clip(pos[1], limites["min_y"], limites["max_y"])
    pos[2] = np.clip(pos[2], limites["min_z"], limites["max_z"])
    
    # --- 2. Colisiones con la casa ---
    
    # Dimensiones de la planta baja
    casa_min_x = -3.5
    casa_max_x = 3.5
    casa_min_z = -4.5
    casa_max_z = 6.0
    piso_casa = -2.0
    techo_casa = 3.0
    
    # Dimensiones del segundo piso
    segundo_min_x = -2.0
    segundo_max_x = 3.5
    segundo_min_z = -4.5
    segundo_max_z = 6.0
    piso_segundo = 3.0
    techo_segundo = 6.0
    
    # --- 2.1. Colisiones con la planta baja ---
    if (casa_min_x <= pos[0] <= casa_max_x and 
        casa_min_z <= pos[2] <= casa_max_z):
        
        # Si estamos dentro del volumen de la casa en X y Z
        if piso_casa < pos[1] < techo_casa:
            # Dentro de la casa - no hay colisión con paredes internas
            pass
        elif pos[1] <= piso_casa:
            # Colisión con el piso
            pos[1] = piso_casa + 0.01
        elif pos[1] >= techo_casa:
            # Colisión con el techo
            pos[1] = techo_casa - 0.01
    
    # --- 2.2. Colisiones con el segundo piso ---
    if (segundo_min_x <= pos[0] <= segundo_max_x and 
        segundo_min_z <= pos[2] <= segundo_max_z):
        
        if piso_segundo < pos[1] < techo_segundo:
            # Dentro del segundo piso
            pass
        elif pos[1] <= piso_segundo:
            # Colisión con el piso del segundo nivel
            pos[1] = piso_segundo + 0.01
        elif pos[1] >= techo_segundo:
            # Colisión con el techo del segundo nivel
            pos[1] = techo_segundo - 0.01
    
    # --- 3. Colisiones con las escaleras ---
    escalera_min_x = -5.0  # -3.5 (pared) - 1.5 (ancho)
    escalera_max_x = -3.5
    escalera_min_z = 3.5 - 28*0.3  # Z final
    escalera_max_z = 3.5
    
    if (escalera_min_x <= pos[0] <= escalera_max_x and 
        escalera_min_z <= pos[2] <= escalera_max_z):
        
        # Calcular altura esperada en este punto de las escaleras
        progreso = (pos[2] - escalera_min_z) / (escalera_max_z - escalera_min_z)
        altura_esperada = -2.0 + (1 - progreso) * (5.0)  # Altura total de las escaleras
        
        # Margen para el personaje
        if pos[1] < altura_esperada:
            pos[1] = altura_esperada + 0.1  # Empujar hacia arriba
        elif pos[1] > altura_esperada + 0.5:
            pos[1] = altura_esperada + 0.5  # Limitar altura máxima
    
    # --- 4. Colisión con la puerta ---
    if (abs(pos[2] - 6.0) < 0.5 and  # Cerca de la puerta en Z
        -0.8 <= pos[0] <= 0.8 and     # Dentro del ancho de la puerta
        pos[1] < 1.0):                # Debajo del dintel
        
        # Si estamos intentando atravesar la puerta
        if pos[2] > 6.0:  # Intentando entrar
            pos[2] = 6.0 - 0.1
        else:  # Intentando salir
            pos[2] = 6.0 + 0.1
    
    # --- 5. Colisión con el hueco de las escaleras al segundo piso ---
    if (-3.5 <= pos[0] <= -2.5 and 
        4.0 <= pos[2] <= 5.0 and 
        techo_casa <= pos[1] <= piso_segundo):
        # Permitir el paso (no hay colisión aquí)
        pass
    elif (casa_min_x <= pos[0] <= casa_max_x and 
          casa_min_z <= pos[2] <= casa_max_z and
          techo_casa <= pos[1] <= piso_segundo):
        # En el espacio entre pisos pero no en las escaleras -> colisión
        pos[1] = techo_casa - 0.1
    
    return pos
    

limites_arbol_derecho = {
    "min_x_d": 10.0,
    "max_x_d": 12.0,
    "min_z_d": -2.2,
    "max_z_d":  5.0,
    "min_y_d": -10.5,  
    "max_y_d": -12.5
    
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
        
    # Colisiones con el árbol derecho
    if (8.7 <= nueva_pos[0] <= 13.3) and (-13.3 <= nueva_pos[2] <= -8.7):
        return camera_pos.copy()
    
    # Colisiones con el árbol izquierdo
    if (-13.3 <= nueva_pos[0] <= -8.7) and (-13.3 <= nueva_pos[2] <= -8.7):
        return camera_pos.copy()

    if colision and not colision_piso: # Si hay colisión pero no con el piso, reproducir sonido
        reproducir_efecto_sonido('C:\\Medical-room-repo\\Medical-rom\\hit1.mp3')
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

#Funcion para poder procesar las entradas atravez del teclado
def process_input(window):
    global camera_pos

    camera_speed = speed
    direction = np.cross(camera_front, camera_up)

    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        nueva_pos = camera_pos + camera_speed * camera_front
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        nueva_pos = camera_pos - camera_speed * camera_front
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        nueva_pos = camera_pos - camera_speed * direction
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        nueva_pos = camera_pos + camera_speed * direction
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)
    if glfw.get_key(window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS:
        nueva_pos = camera_pos - camera_speed * camera_up
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
        nueva_pos = camera_pos + camera_speed * camera_up
        camera_pos[:] = actualizar_posicion_con_colision(nueva_pos, limites)


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

    pitch = max(-89.0, min(89.0, pitch))

    front = np.array([
        math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)),
        math.sin(math.radians(pitch)),
        math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
    ], dtype=np.float32)
    camera_front[:] = front / np.linalg.norm(front)

def dibujar_escaleras():
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_Madera)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    
    ancho_escalera = 1.5
    num_escalones = 30
    altura_total = 5.0
    altura_escalon = altura_total / num_escalones
    profundidad_escalon = 0.25
    
    x_pegado = -3.5
    x_sobresale = x_pegado - ancho_escalera
    
    z_inicio = 5.5
    
    glColor3f(0.85, 0.85, 0.85)
    for i in range(num_escalones):
        y_base = -2.0 + i * altura_escalon
        z_pos = z_inicio - i * profundidad_escalon
        
        # Huella horizontal
        glBegin(GL_QUADS)
        glVertex3f(x_pegado, y_base, z_pos)
        glVertex3f(x_pegado, y_base, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos)
        glEnd()
        
        # Contrahuella vertical (frente del escalón)
        glBegin(GL_QUADS)
        glVertex3f(x_pegado, y_base, z_pos - profundidad_escalon)
        glVertex3f(x_pegado, y_base + altura_escalon, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base + altura_escalon, z_pos - profundidad_escalon)
        glVertex3f(x_sobresale, y_base, z_pos - profundidad_escalon)
        glEnd()
    
    glColor3f(0.9, 0.9, 0.9)
    
    plataforma_retroceso = 2.5
    z_final_escaleras = z_inicio - (num_escalones * profundidad_escalon)
    y_final = -2.0 + num_escalones * altura_escalon  # justo al nivel del último escalón
    
    glBegin(GL_QUADS)
    glVertex3f(x_pegado, y_final, z_final_escaleras)
    glVertex3f(x_pegado, y_final, z_final_escaleras - plataforma_retroceso)
    glVertex3f(x_sobresale, y_final, z_final_escaleras - plataforma_retroceso)
    glVertex3f(x_sobresale, y_final, z_final_escaleras)
    glEnd()



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

    # --- Techo 
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
    
    
    #
    # --- Paredes del segundo piso (más pequeño que el primero) ---
    
         # --- Pared derecha (reducida a X=3.5) ---
    glBindTexture(GL_TEXTURE_2D, textura_pared)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(3.5, 3.0, -4.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(3.5, 3.0, 1.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(3.5, 8.0, 1.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(3.5, 8.0, -4.5)
    glEnd()

    # --- Pared frontal con puerta ---
    # Izquierda de la puerta
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
        # ===== BARANDAS CON TEXTURA (medio unidad hacia adelante) =====
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
    
    # Parte frontal (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -8.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -8.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -8.0)
    glEnd()
    
    # Parte trasera (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glEnd()
    
    # Parte izquierda (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 5.5, -8.0)
    glEnd()
    
    # Parte derecha (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -8.0)
    glEnd()
    
    # Parte inferior (frontal)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 5.5, -8.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 5.5, -8.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -10.0)
    glEnd()
    
    # Parte frontal (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glEnd()
    
    # Parte trasera (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -15.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -15.0)
    glEnd()
    
    # Parte izquierda (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(13.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(13.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(13.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(13.0, 5.5, -13.0)
    glEnd()
    
    # Parte derecha (trasera)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(9.0, 8.0, -13.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(9.0, 8.0, -15.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(9.0, 5.5, -15.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(9.0, 5.5, -13.0)
    glEnd()
    
    # Parte inferior (trasera)
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
    
    # --- Tronco del árbol ---
    # Parte frontal 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(10.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(12.0, 5.0, -10.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(12.0, -2.5, -10.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(10.0, -2.5, -10.5)
    glEnd()
    
    # Parte trasera 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(10.0, 5.0, -12.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(12.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(12.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(10.0, -2.5, -12.5)
    glEnd()
    
    # Parte izquierda 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(12.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(12.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(12.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(12.0, -2.5, -10.5)
    glEnd()
    
    # Parte derecha 
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(10.0, 5.0, -10.5)
    glTexCoord2f(1.0, 0.0); glVertex3f(10.0, 5.0, -12.5)
    glTexCoord2f(1.0, 1.0); glVertex3f(10.0, -2.5, -12.5)
    glTexCoord2f(0.0, 1.0); glVertex3f(10.0, -2.5, -10.5)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    dibujar_hojas_derecho()  # Llamar a la función para dibujar las hojas del árbol
    
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

    global textura_cielo, textura_Madera, textura_pared, textura_techo, textura_suelo, textura_pasto, textura_puerta
    global textura_arbol, textura_hojas, prev_time, accumulated_move, cam_pos
    
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
    
    # Inicializar sonido
    inicializar_sonido('C:\\Medical-room-repo\\Medical-rom\\Minecraft.mp3')
    reproducir_sonido_ambiente(loop=True)
    
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
        dibujar_arbol_izquierdo() #Dibujar el árbol en la parte izquierda
        dibujar_arbol_derecho() #Dibujar el árbol en la parte derecha

        
        #Intercambiar buffers y procesar eventos
        glfw.swap_buffers(ventana)  #Muestra lo que se ha dibujado
        glfw.poll_events()  #Captura eventos del teclado, mouse, etc.

    glfw.terminate()
    
main()