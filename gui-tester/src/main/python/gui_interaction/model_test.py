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
import time
from pynput import keyboard
import data_loader
import signal
import timeit
from test_helper import get_window_size, screenshot, perform_interaction, is_running

running = True

debug = False

quit_counter = 3

working_dir = ""
aut_command = ""
process_id = -1

pyautogui.FAILSAFE = False # disables the fail-safe


def on_release(key):
    global running, quit_counter
    if key == keyboard.Key.f1:
        quit_counter -= 1
        if quit_counter == 0:
            running = False
            print("[Detection] Killing tester.")


sub_window = False


def kill_old_process():
    global process_id

    if process_id != -1:
        os.killpg(os.getpgid(process_id.pid), signal.SIGTERM)
        process_id = -1


def start_aut():
    global working_dir, aut_command, process_id

    if aut_command != "":

        print("[Detection] Starting AUT")

        kill_old_process()

        os.chdir(working_dir)

        with open('stdout.log', "a+") as outfile:
            with open('stderr.log', "a+") as errfile:
                outfile.write("\n" + str(time.time()) + "\n")
                process_id = subprocess.Popen(aut_command.split(), stdout=outfile, stderr=errfile, preexec_fn=os.setsid)

        time.sleep(10)
    else:
        print("[Detection] Could not find AUT to start!")


def convert_coords(x, y, w, h, aspect):
    if aspect > 1:  # width is bigger than height
        h = h * aspect
        y = 0.5 + ((y - 0.5) * aspect)
    elif aspect < 1:
        w = w / aspect
        x = 0.5 + ((x - 0.5) / aspect)

    return x, y, w, h

def select_random_box(proc_boxes):
    # prob_dist = proc_boxes[..., 5] / sum(proc_boxes[..., 5])
    #
    # rand_index = np.random.choice(proc_boxes.shape[0], 1, p=prob_dist)

    best_box = random.sample(proc_boxes.tolist(), 1)[0]

    return best_box


def prepare_screenshot(raw_image):
    st = time.time()
    raw_image = data_loader.pad_image(raw_image)
    et = time.time()
    if debug:
        print("[Detection] PADDING:", et - st)
        cv2.imshow('image',raw_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


    image = cv2.resize(raw_image, (cfg.width, cfg.height))
    #
    # x, y, w, h = convert_coords(0.3, 0.3, 0.4, 0.4, aspect)
    # cv2.rectangle(image,
    #               (int(x*cfg.width), int(y*cfg.height)),
    #               (int(x+w*cfg.width), int(y+h*cfg.height)),
    #               (1, 1, 0.3), -1, 8)
    #
    # cv2.imshow('image',image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    images = np.reshape(image, [1, cfg.width, cfg.height, 1])

    imgs = (images / 127.5) - 1

    return imgs


def convert_boxes(boxes):
    return yolo.convert_net_to_bb(boxes, filter_top=False)[0]


if __name__ == '__main__':
    # Collect events until released
    with keyboard.Listener(on_release=on_release) as listener:
        if len(sys.argv) > 1:
            cfg.window_name = sys.argv[1]

        event = 0

        yolo = Yolo()

        yolo.create_network()

        saver = tf.train.Saver()

        model_file = os.getcwd() + "/" + cfg.weights_dir + "/model.ckpt"

        # config = tf.ConfigProto(allow_soft_placement = True)

        config = tf.ConfigProto(
            device_count={'GPU': 0}
        )

        states = []

        runtime = round(time.time())

        output_dir = cfg.output_dir + "/" + str(runtime)
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        except:
            pass

        try:
            if not os.path.exists(output_dir + "/images"):
                os.makedirs(output_dir + "/images")
        except:
            pass



        test_file = output_dir + "/test.txt"

        with open(test_file, "w+") as t_f:
            t_f.write("")

        with tf.Session(config=config) as sess:

            init_op = tf.global_variables_initializer()
            model = sess.run(init_op)
            if os.path.isfile(os.getcwd() + "/" + cfg.weights_dir + "/checkpoint"):
                saver.restore(sess, model_file)
                print("[Detection] Restored model")
            else:
                print("Cannot find weights file!", os.getcwd() + "/" + cfg.weights_dir + "/checkpoint", "not found!")
                sys.exit(1)

            if len(sys.argv) > 3:
                working_dir = sys.argv[2]
                aut_command = sys.argv[3]

                start_aut()

            yolo.set_training(False)

            anchors = np.reshape(np.array(cfg.anchors), [-1, 2])

            start_time = time.time()

            last_image = None

            boxes = []

            interactions = []

            runtime = cfg.test_time  # 5 mins

            last_u_input = ""

            actions = 0



            csv_file = cfg.log_dir + "/" + str(start_time) + "-test.csv"

            with open(csv_file, "w+") as p_f:
                p_f.write("time,actions,technique,iteration_time,window_name\n")

            while is_running(start_time, runtime, actions, running):

                iteration_time = time.time()

                time.sleep(1)

                exec_time = time.time() - start_time

                os.system('killall "firefox"')

                app_x, app_y, app_w, app_h = get_window_size(cfg.window_name)

                counter = 0

                while app_w == 0:

                    start_aut()
                    counter += 1
                    app_x, app_y, app_w, app_h = get_window_size(cfg.window_name)
                    if counter >= 3:
                        print("[Detection] Couldn't find application window!")
                        break

                if not is_running(start_time, runtime, actions, running):
                    break

                # image = pyautogui.screenshot(region=(app_x, app_y, app_w, app_h)).convert("L")

                # image = ImageGrab.grab(bbox=(app_x, app_y, app_w, app_h)).convert("L")
                image = screenshot()

                if not cfg.fullscreen:
                    image = image[app_y:app_y+app_h, app_x:app_x+app_w]

                image = np.array(image)

                # raw_image = image[app_y:app_y+app_h, app_x:app_x+app_w]

                ih, iw = image.shape[:2]

                aspect = iw / ih

                imgs = prepare_screenshot(image)

                gen_boxes = True

                for l in states:
                    diff = np.sum(np.square(image - l[0])) / image.size
                    if diff < 2:
                        gen_boxes = False
                        proc_boxes = l[1]

                last_image = image

                if True: #gen_boxes or len(proc_boxes) < 3:

                    # print("New state found!", len(states), "states found total.")

                    st = time.time()

                    boxes = sess.run(yolo.output, feed_dict={
                        yolo.x: imgs,
                        yolo.anchors: anchors,
                    })

                    et = time.time()
                    if debug:
                        print("[Detection] ANN:", et - st)

                    st = time.time()
                    p_boxes = convert_boxes(boxes)

                    # pbi = 0
                    # while pbi < p_boxes.shape[0]:
                    #     pb = p_boxes[pbi]
                    #     if pb[5] < cfg.object_detection_threshold:
                    #         p_boxes = np.delete(p_boxes, pbi, axis=0)
                    #     else:
                    #         pbi += 1

                    et = time.time()
                    if debug:
                        print("[Detection] CONVERT:", et - st)

                    # total = np.sum(p_boxes[:,5])
                    #
                    # p_boxes[:,5] = p_boxes[:,5]/total

                    p_boxes = p_boxes[p_boxes[..., 5] > cfg.object_detection_threshold]

                    proc_boxes = p_boxes  # .tolist()

                    # states.append([image, prappoc_boxes])

                for box_num in range(1):

                    if len(proc_boxes) < 1:
                        cfg.object_detection_threshold *= 0.9
                        continue

                    # highest_conf = proc_boxes[0][5]
                    # best_box = proc_boxes[0]

                    best_box = select_random_box(proc_boxes)

                    # best_box = random.sample(proc_boxes, 1)[0]

                    rand_num = random.random()

                    # for b in proc_boxes:
                    #     #if (b[5] > highest_conf):
                    #     rand_num -= b[5]
                    #     if rand_num <= 0:
                    #         #highest_conf = b[5]
                    #         best_box = b
                    #         break;

                    # np.delete(proc_boxes, best_box)

                    height, width = image.shape[:2]

                    current_box = best_box

                    best_box[1:5] = convert_coords(best_box[1], best_box[2], best_box[3], best_box[4], aspect)

                    perform_interaction(best_box, app_x, app_y, app_w, app_h)

                    actions += 1

                    # proc_boxes.remove(current_box)

                # if sub_window:
                #     if random.random() < 0.05:
                #         pyautogui.press('escape')

                end_iteration_time = time.time()
                if debug:
                    print("[Detection] Iteration Time:", end_iteration_time - iteration_time)

                # write test info
                with open(csv_file, "a") as p_f:
                    p_f.write(str(exec_time) + "," + str(actions) + ",detection," + str(
                        iteration_time) + "," + cfg.window_name + "\n")

            # print("Writing concrete tests")
            #
            # # write python regression test
            # python_file = output_dir + "/test.py"
            #
            # # write visual test
            # html_file = output_dir + "/test.html"
            #
            # with open(python_file, "w+") as p_f:
            #     # TODO: Write python functions for click, type, etc
            #     p_f.write("")
            #
            # with open(html_file, "w+") as h_f:
            #     h_f.write("<html><head><title>Test " + str(runtime) + "</title></head>\n"
            #                 "<body>")
            #
            # for i in interactions:
            #     with open(python_file, "a+") as p_f:
            #         # write python regression test
            #         p_f.write("click(" + str(i[1]) + ")\n")
            #         if i[0] == "text_field":
            #             p_f.write("type(" + i[2] + ")\n")
            #
            #     with open(html_file, "a+") as h_f:
            #         # write python regression test
            #         output_img = output_dir + "/images/" + str(i[1]) + ".jpg"
            #         h_f.write("<br />click( <img src='" + output_img + "' /> )<br />\n")
            #         if i[0] == "text_field":
            #             h_f.write("type(" + i[2] + ")<br />\n")
            #
            #
            # with open(html_file, "a+") as h_f:
            #     h_f.write("</body></html>")

            kill_old_process()

            time.sleep(20)
            print("[Detection] Finished testing!")
