from OpenGL.GL import *

def crear_vbo(vertices, uvs, indices):
    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    vbo_uvs = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_uvs)
    glBufferData(GL_ARRAY_BUFFER, uvs.nbytes, uvs, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    vbo_indices = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, vbo_indices)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    return vbo_vertices, vbo_uvs, vbo_indices, len(indices), indices.dtype

def dibujar_vbo(vbo_vertices, vbo_uvs, vbo_indices, num_indices, textura_id, index_type=GL_UNSIGNED_INT):
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)

    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glVertexPointer(3, GL_FLOAT, 0, None)

    glBindBuffer(GL_ARRAY_BUFFER, vbo_uvs)
    glTexCoordPointer(2, GL_FLOAT, 0, None)

    glBindTexture(GL_TEXTURE_2D, textura_id)
    glEnable(GL_TEXTURE_2D)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, vbo_indices)
    glDrawElements(GL_TRIANGLES, num_indices, index_type, None)

    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisable(GL_TEXTURE_2D)