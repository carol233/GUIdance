from __future__ import print_function
import numpy as np
import tensorflow as tf
import random
import csv
import os
from six.moves import cPickle as pickle
import matplotlib.pyplot as plt
import math
import sys
from sklearn import decomposition
from sklearn import preprocessing

learning_rate_start = 1.0
learning_rate_min = 0.001
learning_rate_decay = 0.995
epochs = 10000
batch_size = 256
percent_training = 0.7
percent_testing = 1
percent_validation = 0.5
hidden_layers = [4900, 4096, 256]
sd = 0.05
sdw = 0.05
show_output_image = True
image_height = 64
TRAIN_MODEL = False

TRAIN_AUTOENCODER = True

raw_data = []
output = []
wd = os.getcwd()
for i in range(1, len(sys.argv)):
    os.chdir(os.path.join(wd, sys.argv[i]))
    print("loading", sys.argv[i])
    with open('training_inputs.csv', 'rt') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        counter = len(raw_data)
        for row in reader:
            raw_data.append([])
            for e in row:
                raw_data[counter].append(float(e))
            counter += 1

    with open('training_outputs.csv', 'rt') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        counter = len(output)
        for row in reader:
            output.append([])
            for e in row:
                output[counter].append(float(e))
            counter += 1

os.chdir(wd)

raw_data = np.array(raw_data)
output = np.array(output)

compressed_features = 64 * 64

preop = {
    'pca': decomposition.PCA(n_components=compressed_features, whiten=True),
    'scalar': preprocessing.MinMaxScaler(feature_range=(-1, 1))
}


def whiten_data(d):
    global preop
    return preop['pca'].transform(d)


image_features = image_height * image_height

# raw_data = raw_data[:, :]

whitened_data = np.copy(raw_data[:, 0:image_features])
print("Fitting data")
preop['pca'].fit(whitened_data)

print("Whitening data")

whitened_data = whiten_data(whitened_data)

preop['scalar'].fit(whitened_data)
whitened_data = preop['scalar'].transform(whitened_data)

file_Name = "pca.pickle"
fileObject = open(file_Name, 'wb')
print("Writing pca pickle")
pickle.dump(preop, fileObject)
fileObject.close()

print("Whitened Data: mean: " + str(np.mean(whitened_data)) + " var: " + str(np.var(whitened_data)) +
      " range: (" + str(np.min(whitened_data)) + "," + str(np.max(whitened_data)) + ")")
data = np.copy(raw_data[:, image_features:(image_features + 4)])

data = np.insert(data, [0], whitened_data, axis=1)

rem_features = data.shape[1] % compressed_features

output = np.array(output)

print("Data Shape:", data.shape, output.shape)


def get_sample(data, output, n):
    samples = random.sample(range(data.shape[0]), n)
    return data[samples], output[samples], samples


print("Writing proc data")
np.savetxt("data.csv", whitened_data[0:2000, :].flatten(), delimiter=",")

train_dataset, train_labels, samples = get_sample(data, output, int(percent_training * data.shape[0]))
data = np.delete(data, samples, axis=0)

valid_dataset, valid_labels, samples = get_sample(data, output, int(percent_validation * data.shape[0]))
data = np.delete(data, samples, axis=0)

test_dataset, test_labels, _ = get_sample(data, output, int(percent_testing * data.shape[0]))

print('Training set', train_dataset.shape, train_labels.shape)
print('Validation set', valid_dataset.shape, valid_labels.shape)
print('Test set', test_dataset.shape, test_labels.shape)

x = tf.placeholder(tf.float32, [None, data.shape[1]])

x_img_raw = tf.slice(x, [0, 0], [-1, compressed_features])

# x_img = tf.subtract(tf.multiply(x_img_raw, 2.0), 1.0)

x_rem = tf.slice(x, [0, compressed_features], [-1, -1])

y = tf.placeholder(tf.float32, [None, output.shape[1]])


def weight_variable(shape):
    initial = tf.random_uniform(shape, minval=-1, maxval=1)
    return tf.Variable(initial)


def bias_variable(shape):
    initial = tf.random_uniform(shape, minval=-1, maxval=1)
    return tf.Variable(initial)


W_img_inpt = weight_variable([compressed_features, 24 * 24])
b_img_inpt = bias_variable([24 * 24])

W_img_inpt2 = weight_variable([24 * 24, 16 * 16])
b_img_inpt2 = bias_variable([16 * 16])

h_auto_fc1 = tf.nn.tanh(tf.add(tf.matmul(x_img_raw, W_img_inpt), b_img_inpt))

h_auto_fc2 = tf.nn.tanh(tf.add(tf.matmul(h_auto_fc1, W_img_inpt2), b_img_inpt2))

W_auto_decoder = weight_variable([16 * 16, 24 * 24])
b_auto_decoder = bias_variable([24 * 24])

W_auto_decoder2 = weight_variable([24 * 24, compressed_features])
b_auto_decoder2 = bias_variable([compressed_features])

auto_encoder_step = tf.nn.sigmoid(tf.add(tf.matmul(h_auto_fc2, W_auto_decoder), b_auto_decoder))

auto_encoder_ = tf.nn.sigmoid(tf.add(tf.matmul(auto_encoder_step, W_auto_decoder2), b_auto_decoder2))

loss_auto_encoder = tf.reduce_mean(tf.pow(x_img_raw - auto_encoder_, 2))

learning_rate = tf.placeholder(tf.float32)
# tf.train.AdadeltaOptimizer(learning_rate, 0.95, 1e-08, False)
#
train_auto_encoder_step = tf.train.RMSPropOptimizer(learning_rate).minimize(loss_auto_encoder)

accuracy_auto_encoder = tf.add(1.0,
                               -tf.div(tf.reduce_mean(tf.losses.absolute_difference(x_img_raw, auto_encoder_)), 2.0))

# auto_encoder_out = tf.multiply(tf.add(auto_encoder_, 1.0), 0.5)

h_fcl_joined = tf.concat([auto_encoder_, x_rem], 1)

keep_prob = tf.placeholder(tf.float32)
h_fc1_drop = tf.nn.dropout(h_fcl_joined, keep_prob)

W_fc2 = weight_variable([compressed_features + rem_features, 256])
b_fc2 = bias_variable([256])

h_fcl2 = tf.tanh(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)

W_fc3 = weight_variable([256, rem_features])
b_fc3 = bias_variable([rem_features])

y_ = tf.tanh(tf.matmul(h_fcl2, W_fc3) + b_fc3)

print("model created successfully")

loss = tf.losses.mean_squared_error(y, y_)

# learning_rate = tf.placeholder(tf.float32, shape=[])

# train_step = tf.train.GradientDescentOptimizer(learning_rate).minimize(loss)
train_step = tf.train.AdadeltaOptimizer(learning_rate, 0.95, 1e-08, False).minimize(loss)

accuracy = tf.add(1.0, -tf.div(tf.reduce_mean(tf.losses.absolute_difference(y, y_)), 2.0))

tf.summary.scalar('accuracy', accuracy)

merged = tf.summary.merge_all()
writer = tf.summary.FileWriter('tf')

saver = tf.train.Saver()

plt.close('all')

plt.figure(1)

plots = 1

# start the session
if TRAIN_MODEL:
    with tf.Session() as sess:

        sess.run(tf.global_variables_initializer())

        # Restore variables from disk.
        model_file = "model/model.ckpt"
        # if os.path.isfile("model/checkpoint"):
        #     saver.restore(sess, model_file)
        #     print("Model restored.")

        total_len = train_labels.shape[0]

        count = 0

        learn_rate = learning_rate_start

        for epoch in range(epochs):

            c = list(zip(train_dataset, train_labels))

            random.shuffle(c)

            train_dataset, train_labels = zip(*c)

            for i in range(0, total_len, batch_size):
                samples = range(i, i + total_len)
                batch_x = train_dataset[samples]
                batch_y = train_labels[samples]

                sess.run(train_step, feed_dict={x: batch_x, y: batch_y, keep_prob: 0.95,
                                                learning_rate: learn_rate})

            learn_rate = max(learn_rate * learning_rate_decay, learning_rate_min)

            opt = str(epoch) + "," + \
                  str(sess.run(accuracy, feed_dict={x: valid_dataset, y: valid_labels, keep_prob: 1.0})) + \
                  "," + str(sess.run(accuracy, feed_dict={x: train_dataset, y: train_labels, keep_prob: 1.0}))

            print(opt)

            with open("training_out.log", "a") as myfile:
                myfile.write(opt + "\n")

            if epoch % 50 == 0:
                os.chdir(wd + "/model")
                save_path = saver.save(sess, str(epoch) + model_file)
                print("Model saved in file: %s" % save_path)
                os.chdir(wd)

        print("\nTraining complete!")
        writer.add_graph(sess.graph)

        opt = "-1," + str(sess.run(accuracy, feed_dict={x: test_dataset, y: test_labels, keep_prob: 1.0}))

        print(opt)

        with open("training_out.log", "a") as myfile:
            myfile.write(opt + "\n")

        print()

        save_path = saver.save(sess, model_file)
        print("Model saved in file: %s" % save_path)

elif TRAIN_AUTOENCODER:
    # Auto-encoder
    with tf.Session() as sess:

        sess.run(tf.global_variables_initializer())

        # Restore variables from disk.
        model_file = "model_encoding/model.ckpt"
        # if os.path.isfile("model/checkpoint"):
        #     saver.restore(sess, model_file)
        #     print("Model restored.")

        total_len = train_labels.shape[0]

        count = 0

        learn_rate = learning_rate_start
        header = "epoch,valid_loss,train_loss,learn_rate"

        with open("encoding_out.log", "w") as myfile:
            myfile.write(header + "\n")

        for epoch in range(epochs):
            c = list(zip(train_dataset, train_labels))

            random.shuffle(c)

            train_dataset, train_labels = zip(*c)

            for i in range(0, total_len, batch_size):
                samples = slice(i, i + total_len)
                batch_x = train_dataset[samples]
                batch_y = train_labels[samples]
                sess.run(train_auto_encoder_step, feed_dict={x: batch_x,
                                                             learning_rate: learn_rate})

            opt = str(epoch) + "," + str(sess.run(loss_auto_encoder, feed_dict={x: valid_dataset})) + \
                "," + str(sess.run(loss_auto_encoder, feed_dict={x: train_dataset})) + "," + str(learn_rate)

            learn_rate = max(learn_rate * learning_rate_decay, learning_rate_min)

            print(opt)

            with open("encoding_out.log", "a") as myfile:
                myfile.write(opt + "\n")

            if epoch % 50 == 0:
                os.chdir(wd + "/model_encoding")
                save_path = saver.save(sess, str(epoch) + model_file)
                print("Model saved in file: %s" % save_path)
                os.chdir(wd)

            if epoch % 5 == 0:
                os.chdir(wd + "/model_encoding")
                save_path = saver.save(sess, "tmp" + model_file)
                os.chdir(wd)

        print("\nTraining complete!")
        writer.add_graph(sess.graph)

        opt = str(epochs) + "," + str(sess.run(accuracy_auto_encoder, feed_dict={x: test_dataset}))

        print(opt)

        print()

        save_path = saver.save(sess, model_file)
        print("Model saved in file: %s" % save_path)