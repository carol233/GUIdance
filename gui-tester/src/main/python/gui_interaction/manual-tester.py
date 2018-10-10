import config as cfg
from yolo import Yolo
import cv2
import numpy as np
import tensorflow as tf
import sys
import gc
import math
import random
import os
import pyautogui
from operator import itemgetter
import time
import subprocess
import Xlib
sub_window = False
def get_window_size(window_name):
    global sub_window
    try:
        display = Xlib.display.Display()
        root = display.screen().root

        win_names = window_name.split(":")

        win_names.append("java") # java file browser

        windowIDs = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'), Xlib.X.AnyPropertyType).value
        wid = 0
        win = None
        for windowID in windowIDs:
            window = display.create_resource_object('window', windowID)
            name = window.get_wm_name() # Title
            tags = window.get_wm_class()
            if tags != None and len(tags) > 1:
                name = tags[1]
            print(window.get_wm_class())
            if isinstance(name, str):
                for w_n in win_names:
                    if w_n.lower() in name.lower():
                        # if wid != 0:
                        #     sub_window = True
                        #     if random.random() < 0.05:
                        #         print("Killing window")
                        #         os.system("xkill -id " + wid)
                        wid = windowID
                        win = window
                        window.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
                        window.configure(stack_mode=Xlib.X.Above)
                        #prop = window.get_full_property(display.intern_atom('_NET_WM_PID'), Xlib.X.AnyPropertyType)
                        #pid = prop.value[0] # PID

        geom = win.get_geometry()

        app_x, app_y, app_w, app_h = (geom.x, geom.y, geom.width, geom.height)

        try:
            parent_win = win.query_tree().parent

            while parent_win != 0:
                #print(parent_win)
                p_geom = parent_win.get_geometry()
                app_x += p_geom.x
                app_y += p_geom.y
                parent_win = parent_win.query_tree().parent
        except Exception as e:
            print('Screen cap failed: '+ str(e))
        return app_x, app_y, app_w, app_h
    except Exception as e:
        print('Screen cap failed: '+ str(e))
    return 0, 0, 0, 0

def generate_input_string():
    if random.random() < 0.5:
        return "Hello World!"
    else:
        return str(random.randint(-10000, 10000))

if __name__ == '__main__':

    if len(sys.argv) > 1:
        cfg.window_name = sys.argv[1]

    print("Starting in 5 seconds")

    time.sleep(5)


    start_time = time.time()

    runtime = cfg.test_time

    while (time.time() - start_time < runtime):

        os.system('wmctrl -c "firefox"')

        app_x, app_y, app_w, app_h = get_window_size(cfg.window_name)

        while app_w == 0:
            time.sleep(1)
            app_x, app_y, app_w, app_h = get_window_size(cfg.window_name)
            if time.time() - start_time > runtime:
                print("Couldn't find application window!")
                break

        if time.time() - start_time > runtime:
            break

