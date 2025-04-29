import glfw                          # Librería para crear la ventana y controlar eventos
from OpenGL.GL import *              # Importa funciones de OpenGL

#Inicializar GLFW para que todo pueda funcionar
if not glfw.init():
    raise Exception("No se pudo inicializar GLFW")

#Crear una ventana (ancho, alto, título, monitor, contexto compartido)
ventana = glfw.create_window(1000, 700, "Medical Room", None, None)

if not ventana:
    glfw.terminate()
    raise Exception("No se pudo crear la ventana")

#Establecer el contexto de OpenGL en la ventana actual osea que el glfw pueda renderizar cosas dentro de la ventana
glfw.make_context_current(ventana)

#Bucle principal para que pueda mantenerse la ventana
while not glfw.window_should_close(ventana):
    #Establecer el color de fondo (R, G, B, A)
    glClearColor(0.1, 0.2, 0.3, 1)   # Color de fondo: azul oscuro
    glClear(GL_COLOR_BUFFER_BIT)     # Limpia la pantalla con el color anterior

    #Intercambiar buffers y procesar eventos
    glfw.swap_buffers(ventana)       # Muestra lo que se ha dibujado
    glfw.poll_events()               # Captura eventos del teclado, mouse, etc.

#Terminar GLFW cuando se cierra la ventana
glfw.terminate()