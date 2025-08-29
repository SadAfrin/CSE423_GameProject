# main.py
from OpenGL.GLUT import *
from common import win_w, win_h
import block1_ui as ui
import block3_adv as adv

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowPosition(0, 0)
    glutInitWindowSize(win_w, win_h)
    wind = glutCreateWindow(b"Lab Final Project-Relic Rush 3D")

    glutDisplayFunc(ui.showscreen)
    glutKeyboardFunc(ui.keyboard)
    glutSpecialFunc(ui.special)
    glutMouseFunc(ui.mouse)
    glutIdleFunc(ui.idle)

    adv.reset_run()
    glutMainLoop()

if __name__ == "__main__":
    main()
