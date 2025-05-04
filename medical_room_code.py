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

# Función para crear un cubo (una pared, suelo o techo)
def crear_cubo():
    vertices = np.array([
        # -------- PARED FRONTAL (con hueco para puerta) --------
        # Izquierda de la puerta
        -2.0, -2.0,  2.0,
        -0.6, -2.0,  2.0,   
        -0.6,  1.0,  2.0,
        -2.0,  1.0,  2.0,

        # Derecha de la puerta  
        0.6, -2.0,  2.0,
        2.0, -2.0,  2.0,
        2.0,  2.0,  2.0,
        0.6,  2.0,  2.0,

        # Parte superior de la puerta
        -0.6,  1.0,  2.0,
        0.6,  1.0,  2.0,
        0.6,  2.0,  2.0,
        -0.6,  2.0,  2.0,

        # -------- PARED TRASERA --------
        -2.0, -2.0, -2.0,
        2.0, -2.0, -2.0,
        2.0,  2.0, -2.0,
        -2.0,  2.0, -2.0,

        # -------- PARED IZQUIERDA --------
        -2.0, -2.0, -2.0,
        -2.0, -2.0,  2.0,
        -2.0,  2.0,  2.0,
        -2.0,  2.0, -2.0,

        # -------- PARED DERECHA --------
        2.0, -2.0, -2.0,
        2.0, -2.0,  2.0,
        2.0,  2.0,  2.0,
        2.0,  2.0, -2.0,

        # -------- TECHO --------
        -2.0,  2.0, -2.0,
        2.0,  2.0, -2.0,
        2.0,  2.0,  2.0,
        -2.0,  2.0,  2.0,

        # -------- SUELO --------
        -2.0, -2.0, -2.0,
        2.0, -2.0, -2.0,
        2.0, -2.0,  2.0,
        -2.0, -2.0,  2.0
    ], dtype=np.float32) # specificamos que los datos son de tipo float32

    #Definir el buffer de vértices
    #Crear y vincular el VAO (contiene el estado de los vértices)
    VAO = glGenVertexArrays(1)  #Crear el VAO
    glBindVertexArray(VAO)  #Vincular el VAO
    
    #Crear y vincular el VBO (almacena los datos de los vértices)
    VBO = glGenBuffers(1)   #Crear el VBO
    glBindBuffer(GL_ARRAY_BUFFER, VBO)  #Vincular el VBO
    
    #Subir los datos de los vértices al buffer
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)    #Cargar los datos al VBO

    # Configurar el layout de los vértices
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)    #Definir el formato de los datos
    glEnableVertexAttribArray(0)    #Activar el atributo de vértices
    
    return VAO

#Función para dibujar el cuarto
def crear_cuarto():
    glColor3f(1.0, 1.0, 1.0)  # Establecer el color verde para el cubo
    #Crear un cubo para representar las paredes, suelo y techo
    cubo = crear_cubo()
    
    #Dibujar el cubo
    glDrawArrays(GL_QUADS, 0, 24)

# Función para configurar la vista y proyección 3D
def configurar_vision():
    # Definir la proyección en 3D (cámara ortogonal)
    glMatrixMode(GL_PROJECTION)  # Establecer modo de proyección
    glLoadIdentity()  # Limpiar la matriz de proyección
    gluPerspective(45, 1200/900, 0.1, 50.0)  # Ángulo de visión, aspecto, near, far

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Cámara desde arriba y en diagonal (x=5, y=5, z=5), mirando al origen (0,0,0)
    gluLookAt(5, 5, 5,    # Posición de la cámara
              0, 0, 0,    # Punto al que mira la cámara
              0, 1, 0)    # Vector 'arriba'

# Función principal del programa
def main():
    ventana = inicializar_ventana()
    configurar_vision()  # Configurar la visión para 3D

    # Bucle principal
    while not glfw.window_should_close(ventana):
        #Establecemos los colores del fondo gris oscuro
        glClearColor(0.1, 0.1, 0.1, 1.0)
        # Limpiar tanto el buffer de color como el buffer de profundidad
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        crear_cuarto()  # Dibujar el cuarto
        
        #Intercambiar buffers y procesar eventos
        glfw.swap_buffers(ventana)  # Muestra lo que se ha dibujado
        glfw.poll_events()  # Captura eventos del teclado, mouse, etc.

    glfw.terminate()

# Punto de entrada
if __name__ == "__main__":
    main()