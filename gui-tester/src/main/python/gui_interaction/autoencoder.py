# These are all the modules we'll be using later. Make sure you can import them
# before proceeding further.
from __future__ import print_function
import tensorflow as tf


def weight_variable(shape):
    initial = tf.random_normal(shape, mean=0, stddev=0.1)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.random_normal(shape, mean=0, stddev=0.1)
    return tf.Variable(initial)

class AutoEncoder:
    learning_rate = 0.0001
    epochs = 1000
    batch_size = 25
    input_features = 64*64+4
    image_size = 64*64
    hidden_layers_n = [32*32]
    activation_functions = []
    image = None
    hidden_layers = [None]
    output_layer = None
    minimal_layer = None
    loss = None

    keep_prob = tf.placeholder(tf.float32)

    def dropout(self, x):
        return tf.nn.dropout(tf.nn.relu(x), self.keep_prob)

    def __init__(self, image=tf.placeholder(tf.float32, [None, image_size])):
        self.image = image

        #self.activation_functions = [tf.nn.relu, self.dropout,
        #                             tf.nn.relu, tf.nn.sigmoid]

        self.activation_functions = [self.dropout, tf.nn.sigmoid]

        hidden_layers_n = [self.image_size]
        hidden_layers_n.extend(self.hidden_layers_n)

        self.hidden_layers = []
        last_layer = self.image
        last_size = 0

        input_stack = []

        for i in range(0, len(hidden_layers_n)-1):
            weights = weight_variable([hidden_layers_n[i], hidden_layers_n[i+1]])
            biases = bias_variable([hidden_layers_n[i+1]])
            hidden_layer = self.activation_functions[len(self.hidden_layers)](tf.add(tf.matmul(last_layer, weights), biases))
            last_layer = hidden_layer
            self.hidden_layers.append(hidden_layer)
            input_stack.append(hidden_layers_n[i])
            last_size = hidden_layers_n[i+1]

        self.minimal_layer = last_layer

        while len(input_stack) > 0:
            next_layer = input_stack.pop()
            prev_layer = last_size
            weights = weight_variable([prev_layer, next_layer])
            biases = bias_variable([next_layer])
            hidden_layer = self.activation_functions[len(self.hidden_layers)](tf.add(tf.matmul(last_layer, weights), biases))
            last_layer = hidden_layer
            self.hidden_layers.append(hidden_layer)
            last_size = next_layer

        last_layer = self.hidden_layers.pop()
        self.output_layer = last_layer

        self.loss = tf.reduce_mean(tf.square(self.image - self.output_layer))