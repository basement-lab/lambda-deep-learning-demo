"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

"""
from __future__ import print_function
import sys

import tensorflow as tf


class Runner(object):
  def __init__(self, args, inputter, modeler):
    self.args = args
    self.inputter = inputter
    self.modeler = modeler

    self.modeler.num_samples = self.inputter.get_num_samples()
    self.batch_size = self.args.batch_size_per_gpu * self.args.num_gpu

    self.session_config = self.create_session_config()
    self.sess = None
    self.nonreplicated_fns = [self.modeler.create_nonreplicated_fn,
                              self.inputter.create_nonreplicated_fn]    
    self.feed_dict = {}
    self.outputs = None
    self.run_ops = []
    self.run_ops_names = []
    self.saver = None
    self.summary_writer = None

  def create_session_config(self):
    """create session_config
    """
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.95,
                                allow_growth=True)

    # set number of GPU devices
    device_count = {"GPU": self.args.num_gpu}

    session_config = tf.ConfigProto(
      allow_soft_placement=True,
      log_device_placement=False,
      device_count=device_count,
      gpu_options=gpu_options)

    return session_config

  def before_run(self, callbacks):
    for callback in callbacks:
      callback.before_run(self.sess, self.saver)

    self.run_feed_dict()

  def before_step(self, callbacks):
    for callback in callbacks:
      callback.before_step(self.sess)

  def after_step(self, callbacks):

    outputs_dict = {}
    for key, value in zip(self.run_ops_names, self.outputs):
      outputs_dict[key] = value

    print_msg = "\r"
    for callback in callbacks:
      return_dict = callback.after_step(self.sess, outputs_dict,
                                        self.saver, self.summary_writer)
      if return_dict:
        for key in return_dict:
          print_msg = print_msg + return_dict[key] + " "

    if len(print_msg) > 0:
      print(print_msg, end='')
      sys.stdout.flush()

  def after_run(self, callbacks):
    for callback in callbacks:
      callback.after_run(self.sess, self.saver, self.summary_writer)

  def run_feed_dict(self):
      for key in self.modeler.feed_dict_ops:
        self.feed_dict[key] = self.sess.run(
          self.modeler.feed_dict_ops[key])

  def collect_summary(self, run_ops_names, run_ops):
    for name, op in zip(run_ops_names, run_ops):
      if name in self.args.summary_names:
        tf.summary.scalar(name, op)
    return tf.summary.merge_all()

  def collect_ops(self, ops):
    # Create train_op for gradient, keep other ops unchanged
    run_ops = []
    run_ops_names = []

    for key in ops:
      if key == "grads":
        minimize_op = self.modeler.optimizer.apply_gradients(
          ops[key], global_step=self.modeler.global_step)
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        op = tf.group(minimize_op, update_ops)
      else:
        op = ops[key]
      run_ops.append(op)
      run_ops_names.append(key)

    if self.args.mode == "train":
      summary_op = self.collect_summary(run_ops_names, run_ops)
      run_ops.append(summary_op)
      run_ops_names.append("summary")

    return run_ops, run_ops_names

  def print_trainable_variables(self):

    for i in tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES):
      print (i.name)

  def run(self):
    self.create_graph()

    with tf.Session(config=self.session_config) as self.sess:

      # Before run
      self.before_run(self.modeler.callbacks)

      global_step = 0
      if self.args.mode == "train":
        global_step = self.sess.run(self.global_step_op)

      max_step = self.sess.run(self.max_step_op)

      while global_step < max_step:
        self.before_step(self.modeler.callbacks)

        self.outputs = self.sess.run(self.run_ops, feed_dict=self.feed_dict)

        self.after_step(self.modeler.callbacks)

        global_step = global_step + 1

      self.after_run(self.modeler.callbacks)


def build(args, inputter, modeler):
  return Runner(args, inputter, modeler)
