"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

"""
from __future__ import print_function


class Inputter(object):
  def __init__(self, config, augmenter):
    self.config = config
    self.augmenter = augmenter

  def get_num_samples(self, *argv):
    pass

  def parse_fn(self, mode, *argv):
    pass

  def input_fn(self, mode, *argv):
    pass


def build(config, augmenter):
  return Inputter(config, augmenter)
