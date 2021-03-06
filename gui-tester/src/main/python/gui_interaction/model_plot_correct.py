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
from tensorflow.python.tools import inspect_checkpoint as chkp
from data_loader import load_files, disable_transformation, load_raw_image, convert_coords

disable_transformation()



if __name__ == '__main__':

    tf.reset_default_graph()
    yolo = Yolo()

    yolo.create_network()
    #yolo.set_training(False)
    yolo.create_training()

    learning_rate = tf.placeholder(tf.float64)
    learning_r = cfg.learning_rate_start

    saver = tf.train.Saver()

    model_file = os.getcwd() + "/" + cfg.weights_dir + "/model.ckpt"

    #chkp.print_tensors_in_checkpoint_file(model_file, tensor_name='', all_tensors=True)

    gpu_options = tf.GPUOptions(allow_growth=True)

    config = tf.ConfigProto(
        device_count = {'GPU': 0}
    )

    with tf.Session(config=config) as sess:

        init_op = tf.global_variables_initializer()
        model = sess.run(init_op)
        if os.path.isfile(os.getcwd() + "/" + cfg.weights_dir + "/checkpoint"):
            saver.restore(sess, model_file)
            print("Restored model")
        yolo.set_training(False)

        anchors = np.reshape(np.array(cfg.anchors), [-1, 2])
        images, labels, obj_detect = load_files([sys.argv[1]])

        img = images[0]

        #normalise data  between 0 and 1
        imgs = np.array(images)/127.5-1
        labels = np.array(labels)/ cfg.grid_shape[0]
        obj_detect = np.array(obj_detect)

        conf_thresh = 0.1

        boxes, correct, iou = sess.run([yolo.output, yolo.matches, yolo.best_iou], feed_dict={
            yolo.x: imgs,
            yolo.anchors: anchors,
            yolo.train_bounding_boxes: labels,
            yolo.train_object_recognition: obj_detect,
            yolo.iou_threshold: 0.5,
            yolo.object_detection_threshold: conf_thresh
        })

        proc_correct = yolo.convert_correct_to_list(correct)[0]
        # proc_iou = yolo.convert_correct_to_list(np.reshape(iou, [-1, cfg.grid_shape[0], cfg.grid_shape[1]]))[0]
        proc_boxes = yolo.convert_net_to_bb(boxes, filter_top=True)

        labels_classes = np.append(np.expand_dims(obj_detect, axis=-1), labels, axis=-1)

        proc_boxes, iou_max = yolo.calculate_max_iou(proc_boxes, np.reshape(labels_classes, [labels.shape[0], -1, 6]))

        proc_boxes = proc_boxes.tolist()[0]


        img = load_raw_image(sys.argv[1])

        height, width = img.shape[:2]

        trim_overlap = True

        i=0
        while i < len(proc_boxes):
            box = proc_boxes[i]

            box[1:5] = convert_coords(box[1], box[2], box[3], box[4], width/height)

            x, y, w, h = (box[1],box[2],box[3],box[4])
            box[1] = x - w/2
            box[2] = y - h/2
            box[3] = x + w/2
            box[4] = y + h/2
            i = i + 1
        i = 0

        correct_q = 0
        predicted_boxes = 0

        for bc in range(len(proc_boxes)):
            box = proc_boxes[bc]
            if box[5] < conf_thresh:
                continue
            cor = proc_correct[bc]
            height, width = img.shape[:2]

            cls = yolo.names[int(box[0])]

            hex = cls.encode('utf-8').hex()[0:6]

            color = tuple(int(int(hex[k:k+2], 16)*0.75) for k in (0, 2 ,4))

            # if box[6] > 0.3:
            #     correct_q += 1
            #     color = [255, 255, 255]
            # if box[6] < 0.3:
            #     continue

            if (box[5]>cfg.object_detection_threshold):
                print(box)

                predicted_boxes += 1

                x1 = max(int(width*box[1]), 0)
                y1 = max(int(height*box[2]), 0)
                x2 = int(width*box[3])
                y2 = int(height*box[4])

                cv2.rectangle(img, (x1, y1),
                              (x2, y2),
                              (color[0], color[1], color[2]), 1+int(5*box[5]), 8)

        for bc in range(len(proc_boxes)):
            box = proc_boxes[bc]
            if box[5] < conf_thresh:
                continue

            cor = proc_correct[bc]
            cls = yolo.names[int(box[0])]

            hex = cls.encode('utf-8').hex()[0:6]
            color = tuple(int(int(hex[k:k+2], 16)*0.75) for k in (0, 2 ,4))
            # if box[6] > 0.3:
            #     color = [255, 255, 255]
            # if box[6] < 0.3:
            #     continue

            if (box[5]>cfg.object_detection_threshold):
                height, width = img.shape[:2]

                avg_col = (color[0] + color[1] + color[2])/3

                text_col = (255, 255, 255)


                if avg_col > 127:
                    text_col = (0, 0, 0)

                x1 = max(int(width*box[1]), 0)
                y1 = max(int(height*box[2]), 0)
                x2 = int(width*box[3])
                y2 = int(height*box[4])

                cv2.rectangle(img,
                              (x1-3, y1-23),
                              (x1 + (5 + len(cls)+10)*10, y1),
                              (color[0], color[1], color[2]), -1, 8)

                cv2.putText(img, cls + " conf:" + str(round(box[5]*100)) + " iou:" + str(round(box[6]*100)),
                            (x1-3, y1-3),
                            cv2.FONT_HERSHEY_PLAIN,
                            1, text_col, 1, lineType=cv2.LINE_AA)

        actual_labels = np.sum((labels[..., 4]>0).astype(int))

        print(predicted_boxes, ":", actual_labels)

        predicted_boxes = predicted_boxes if predicted_boxes > 0 else 1
        actual_labels = actual_labels if actual_labels > 0 else 1

        print(correct_q, "correct predictions. Precision:", correct_q / (predicted_boxes), "Recall:",
              correct_q / actual_labels)

        print(iou_max)

        cv2.imshow('image',img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
