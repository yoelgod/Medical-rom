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
from PIL import Image
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math


#Variables globales para el movimiento de camara
camera_pos = np.array([0.0, 1.6, 3.0], dtype=np.float32)  #Altura tipo "ojo humano"
camera_front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

yaw = -90.0   #Ángulo horizontal
pitch = 0.0   #Ángulo vertical
lastX = 400   #Última posición del mouse (centro ventana)
lastY = 300
first_mouse = True
speed = 0.01
sensitivity = 0.1


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
        camera_pos[:] += camera_speed * camera_front
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        camera_pos[:] -= camera_speed * camera_front
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        camera_pos[:] -= camera_speed * direction
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        camera_pos[:] += camera_speed * direction
    if glfw.get_key(window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS:
        camera_pos[:] -= camera_speed * camera_up
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
        camera_pos[:] += camera_speed * camera_up


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


# Función para crear un cubo (una pared, suelo o techo)
def dibujar_cuarto():
    # Cargar la textura para el cuarto exterior
    global textura_pared, textura_techo
    
    glColor3f(1.0, 1.0, 1.0)  # Importante: color blanco para no alterar la textura
    
    glEnable(GL_TEXTURE_2D)
    
    #Carga la textura de las paredes
    glBindTexture(GL_TEXTURE_2D, textura_techo)
    
    # --- TECHO ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.0, 2.0, -2.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.0, 2.0, -2.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.0, 2.0, 2.2)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.0, 2.0, 2.2)
    glEnd()
    
    #Carga la textura de las paredes
    glBindTexture(GL_TEXTURE_2D, textura_pared)

    # --- PARED TRASERA ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.0, -2.0, -2.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.0, -2.0, -2.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.0, 2.0, -2.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.0, 2.0, -2.0)
    glEnd()

    # --- PARED IZQUIERDA ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.0, -2.0, -2.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(-2.0, -2.0, 2.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(-2.0, 2.0, 2.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.0, 2.0, -2.0)
    glEnd()

    # --- PARED DERECHA ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(2.0, -2.0, -2.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.0, -2.0, 2.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.0, 2.0, 2.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(2.0, 2.0, -2.0)
    glEnd()

    # --- SUELO ---
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.0, -2.0, -2.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.0, -2.0, -2.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.0, -2.0, 2.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.0, -2.0, 2.0)
    glEnd()

    # --- PARED FRONTAL CON HUECO (puerta sin textura) ---

    # Parte izquierda de la pared frontal
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-2.0, -2.0, 2.0)
    glTexCoord2f(0.3, 0.0); glVertex3f(-0.75, -2.0, 2.0)
    glTexCoord2f(0.3, 0.35); glVertex3f(-0.75, 0.7, 2.0)
    glTexCoord2f(0.0, 0.35); glVertex3f(-2.0, 0.7, 2.0)
    glEnd()

    # Parte derecha de la pared frontal
    glBegin(GL_QUADS)
    glTexCoord2f(0.7, 0.0); glVertex3f(0.75, -2.0, 2.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(2.0, -2.0, 2.0)
    glTexCoord2f(1.0, 0.35); glVertex3f(2.0, 0.7, 2.0)
    glTexCoord2f(0.7, 0.35); glVertex3f(0.75, 0.7, 2.0)
    glEnd()

    # Parte superior de la pared frontal
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.35); glVertex3f(-2.0, 0.7, 2.0)
    glTexCoord2f(1.0, 0.35); glVertex3f(2.0, 0.7, 2.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(2.0, 2.0, 2.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-2.0, 2.0, 2.0)
    glEnd()

    # Desactivamos la textura para dibujar la puerta sin ella
    glDisable(GL_TEXTURE_2D)

    # PUERTA (rectángulo que cubre el hueco)
    glColor3f(1.0, 1.0, 1.0)  # Color blanco
    glBegin(GL_QUADS)
    glVertex3f(-0.75, -2.0, 2.01)
    glVertex3f(0.75, -2.0, 2.01)
    glVertex3f(0.75, 0.7, 2.01)
    glVertex3f(-0.75, 0.7, 2.01)
    glEnd()


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

    global textura_pared, textura_techo
    
    textura_pared = cargar_textura('C:/medical-room-repo/Medical-rom/wall_texture.jpg')
    textura_techo = cargar_textura('C:/medical-room-repo/Medical-rom/roof_texture.jpg')
    
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