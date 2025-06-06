#Librería para crear la ventana y controlar eventos
import glfw
#Importa funciones de OpenGL
from OpenGL.GL import *
#Esta libreria de OpenGL.GL.shaders permite trabajar con shaders para efectos avanzados de gráficos
from OpenGL.GL.shaders import compileProgram, compileShader
#Libreria de numpy facilita el manejo de arreglos y matrices, y se usa para definir las coordenadas de los vértices.
import numpy as np
from OpenGL.GLU import gluPerspective  # Para la proyección de perspectiva
from OpenGL.GL import glLoadIdentity  # Para manejar las matrices de vista
from OpenGL.GLU import gluLookAt
from PIL import Image, ImageOps
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

#Variables globales para el movimiento de camara
camera_pos = np.array([0.0, 1.6, 8.0], dtype=np.float32) #Altura tipo "ojo humano"
camera_front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
camera_pos = np.array([0.0, 1.6, 8.0], dtype=np.float32)

yaw = -90.0   #Ángulo horizontal
pitch = 0.0   #Ángulo vertical
lastX = 400   #Última posición del mouse (centro ventana)
lastY = 300
first_mouse = True
speed = 0.025
sensitivity = 0.15

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
    glDisable(GL_TEXTURE_2D)
    
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
    
    # --- Pared izquierda (con puerta) ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ancho_izq, 3.0, z_trasera)
    glTexCoord2f(1.0, 0.0); glVertex3f(ancho_izq, 3.0, z_frente)
    glTexCoord2f(1.0, 1.0); glVertex3f(ancho_izq, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0); glVertex3f(ancho_izq, 6.0, z_trasera)
    glEnd()
    
    # --- Pared derecha ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ancho_der, 3.0, z_trasera)
    glTexCoord2f(1.0, 0.0); glVertex3f(ancho_der, 3.0, z_frente)
    glTexCoord2f(1.0, 1.0); glVertex3f(ancho_der, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0); glVertex3f(ancho_der, 6.0, z_trasera)
    glEnd()
    
    # --- Pared frontal (más atrás) ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ancho_izq, 3.0, z_frente)
    glTexCoord2f(1.0, 0.0); glVertex3f(ancho_der, 3.0, z_frente)
    glTexCoord2f(1.0, 1.0); glVertex3f(ancho_der, 6.0, z_frente)
    glTexCoord2f(0.0, 1.0); glVertex3f(ancho_izq, 6.0, z_frente)
    glEnd()
    
    # --- Pared trasera ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(ancho_izq, 3.0, z_trasera)
    glTexCoord2f(1.0, 0.0); glVertex3f(ancho_der, 3.0, z_trasera)
    glTexCoord2f(1.0, 1.0); glVertex3f(ancho_der, 6.0, z_trasera)
    glTexCoord2f(0.0, 1.0); glVertex3f(ancho_izq, 6.0, z_trasera)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    
        # --- Puerta del segundo piso (movida al extremo trasero de la misma pared) ---
    glColor3f(0.4, 0.3, 0.2)  # Color madera
    glBegin(GL_QUADS)
    # Mantenemos ancho_izq pero cambiamos las coordenadas Z para ponerla cerca de la pared trasera
    glVertex3f(ancho_izq, 3.0, z_trasera + 1.0)  # Esquina inferior derecha (z_trasera es -4.5)
    glVertex3f(ancho_izq, 3.0, z_trasera + 2.0)  # Esquina inferior izquierda
    glVertex3f(ancho_izq, 5.0, z_trasera + 2.0)  # Esquina superior izquierda
    glVertex3f(ancho_izq, 5.0, z_trasera + 1.0)  # Esquina superior derecha
    glEnd()

    # --- Abertura para escaleras (ajustada para coincidir) ---
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(ancho_izq, 3.0, z_trasera + 1.0)  # Coordenadas Z iguales que la puerta
    glVertex3f(ancho_izq + 1.0, 3.0, z_trasera + 1.0)
    glVertex3f(ancho_izq + 1.0, 3.0, z_trasera + 2.0)
    glVertex3f(ancho_izq, 3.0, z_trasera + 2.0)
    glEnd()
    
    dibujar_escaleras()

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

    global textura_pared, textura_techo, textura_suelo, textura_pasto
    
    textura_pared = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\wall_texture.jpg')
    textura_techo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\roof_texture.jpg')
    textura_suelo = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\floor_texture.jpg')
    textura_pasto = cargar_textura('C:\\Medical-room-repo\\Medical-rom\\garden_texture.jpg')
    
    #Bucle principal
    while not glfw.window_should_close(ventana):
        
        #Limpiar tanto el buffer de color como el buffer de profundidad
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        configurar_vision()  #Configurar la visión para 3D
        process_input(ventana)
        dibujar_cuarto()  #Dibujar el cuarto
        
        #Intercambiar buffers y procesar eventos
        glfw.swap_buffers(ventana)  #Muestra lo que se ha dibujado
        glfw.poll_events()  #Captura eventos del teclado, mouse, etc.

    glfw.terminate()

#Punto de entrada
if __name__ == "__main__":
    main()