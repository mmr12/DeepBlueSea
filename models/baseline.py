from base.base_model import BaseModel
import tensorflow as tf
from models.utils_model import *


class Baseline(BaseModel):

    def __init__(self, config):
        super(Baseline, self).__init__(config)
        self.build_model()
        self.init_saver()

    def build_model(self):
        self.is_training = tf.placeholder(tf.bool)

        self.x = tf.placeholder(tf.float32, shape=[None, 80, 80])
        self.y = tf.placeholder(tf.float32, shape=[None])

        #param
        filter_size_conv1 = 3
        num_filters_conv1 = 32

        filter_size_conv2 = 3
        num_filters_conv2 = 32

        filter_size_conv3 = 3
        num_filters_conv3 = 64

        fc_layer_size = 128

        # network architecture
        layer_conv1 = self.create_convolutional_layer(input=self.x,
                                                 num_input_channels=num_channels,
                                                 conv_filter_size=filter_size_conv1,
                                                 num_filters=num_filters_conv1)

        layer_conv2 = create_convolutional_layer(input=layer_conv1,
                                                 num_input_channels=num_filters_conv1,
                                                 conv_filter_size=filter_size_conv2,
                                                 num_filters=num_filters_conv2)

        layer_conv3 = create_convolutional_layer(input=layer_conv2,
                                                 num_input_channels=num_filters_conv2,
                                                 conv_filter_size=filter_size_conv3,
                                                 num_filters=num_filters_conv3)

        layer_flat = create_flatten_layer(layer_conv3)

        layer_fc1 = create_fc_layer(input=layer_flat,
                                    num_inputs=layer_flat.get_shape()[1:4].num_elements(),
                                    num_outputs=fc_layer_size,
                                    use_relu=True)

        layer_fc2 = create_fc_layer(input=layer_fc1,
                                    num_inputs=fc_layer_size,
                                    num_outputs=2,
                                    use_relu=False)

        with tf.name_scope("loss"):
            self.cross_entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=self.y, logits=layer_fc2))
            self.train_step = tf.train.AdamOptimizer(self.config.learning_rate).minimize(self.cross_entropy,
                                                                                         global_step=self.global_step_tensor)
            correct_prediction = tf.equal(tf.argmax(layer_fc2, 1), tf.argmax(self.y, 1))
            self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


    def init_saver(self):
        # here you initialize the tensorflow saver that will be used in saving the checkpoints.
        self.saver = tf.train.Saver(max_to_keep=self.config.max_to_keep)