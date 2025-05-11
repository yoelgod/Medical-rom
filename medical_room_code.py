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


# Función para inicializar la ventana con tamaño fijo
def inicializar_ventana(titulo="Proyecto OpenGL Paso 1"):
    ancho, alto = 1200, 900  # Tamaño fijo
    if not glfw.init():
        raise Exception("No se pudo inicializar GLFW")

    ventana = glfw.create_window(ancho, alto, titulo, None, None)

    if not ventana:
        glfw.terminate()
        raise Exception("No se pudo crear la ventana")

    #Establecer el contexto de OpenGL en la ventana actual
    glfw.make_context_current(ventana)
    glEnable(GL_DEPTH_TEST)  # Habilitar la prueba de profundidad
    
    return ventana

#FUncion para poder ver la textura
def cargar_textura(ruta):
    # Abrir imagen
    imagen = Image.open(ruta)
    imagen = imagen.transpose(Image.FLIP_TOP_BOTTOM)  # Voltear la imagen para OpenGL

    # Convertir la imagen a un formato adecuado para OpenGL
    ancho, alto = imagen.size
    imagen_data = imagen.tobytes("raw", "RGB", 0, -1)

    # Crear y activar la textura
    textura = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, textura)

    # Configuración de la textura
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, ancho, alto, 0, GL_RGB, GL_UNSIGNED_BYTE, imagen_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    return textura

# Función para crear un cubo (una pared, suelo o techo)
def dibujar_cuarto():
    # Cargar la textura para el cuarto exterior
    textura_pared = cargar_textura('C:/medical-room-repo/Medical-rom/wall_texture.jpg')
    textura_techo = cargar_textura('C:/medical-room-repo/Medical-rom/roof_texture.jpg')
    
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

    # Cámara desde arriba y en diagonal (x=5, y=5, z=5), mirando al origen (0,0,0)
    gluLookAt(5, 5, 5,    # Posición de la cámara
              0, 0, 0,    # Punto al que mira la cámara
              0, 1, 0)    # Vector 'arriba'

# Función principal del programa
def main():
    ventana = inicializar_ventana()
    configurar_vision()  #Configurar la visión para 3D

    #Bucle principal
    while not glfw.window_should_close(ventana):
        #Establecemos los colores del fondo gris oscuro
        glClearColor(0.1, 0.1, 0.1, 1.0)
        #Limpiar tanto el buffer de color como el buffer de profundidad
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        dibujar_cuarto()  #Dibujar el cuarto
        
        #Intercambiar buffers y procesar eventos
        glfw.swap_buffers(ventana)  #Muestra lo que se ha dibujado
        glfw.poll_events()  #Captura eventos del teclado, mouse, etc.

    glfw.terminate()

#Punto de entrada
if __name__ == "__main__":
    main()