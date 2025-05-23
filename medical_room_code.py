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
    "max_y": 3.0 
}

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
    
    glDisable(GL_TEXTURE_2D)

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
    
    textura_pared = cargar_textura('C:\medical-room-rep\Medical-rom/wall_texture.jpg')
    textura_techo = cargar_textura('C:\medical-room-rep\Medical-rom/roof_texture.jpg')
    textura_suelo = cargar_textura('C:\medical-room-rep\Medical-rom/floor_texture.jpg')
    textura_pasto = cargar_textura('C:\medical-room-rep\Medical-rom/garden_texture.jpg')
    
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