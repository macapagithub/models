# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Generates grid anchors on the fly corresponding to multiple CNN layers.

Generates grid anchors on the fly corresponding to multiple CNN layers as
described in:
"Focal Loss for Dense Object Detection"
T.-Y. Lin, P. Goyal, R. Girshick, K. He, P. Dollar
"""

from object_detection.anchor_generators import grid_anchor_generator
from object_detection.core import box_list_ops


class MultiscaleGridAnchorGenerator(object):
  """Generate a grid of anchors for multiple CNN layers."""

  def __init__(self, min_level, max_level, anchor_scale, aspect_ratios,
               scales_per_octave):
    """Constructs a MultiscaleGridAnchorGenerator.

    To construct anchors, at multiple scale resolutions, one must provide a
    the minimum level and maximum levels on a scale pyramid. To define the size
    of anchor, the anchor scale is provided to decide the size relatively to the
    stride of the corresponding feature map. The generator allows one pixel
    location on feature map maps to multiple anchors, that have different aspect
    ratios and intermediate scales.

    Args:
      min_level: minimum level in feature pyramid.
      max_level: maximum level in feature pyramid.
      anchor_scale: anchor scale and feature stride define the size of the base
        anchor on an image. For example, given a feature pyramid with strides
        [2^3, ..., 2^7] and anchor scale 4. The base anchor size is
        4 * [2^3, ..., 2^7].
      aspect_ratios: list or tuple of (float) aspect ratios to place on each
        grid point.
      scales_per_octave: integer number of intermediate scales per scale octave.
    """
    self._anchor_grid_info = []
    self._aspect_ratios = aspect_ratios
    self._scales_per_octave = scales_per_octave

    for level in range(min_level, max_level + 1):
      anchor_stride = [2**level, 2**level]
      scales = []
      aspects = []
      for scale in range(scales_per_octave):
        scales.append(2**(float(scale) / scales_per_octave))
      for aspect_ratio in aspect_ratios:
        aspects.append(aspect_ratio)
      base_anchor_size = [2**level * anchor_scale, 2**level * anchor_scale]
      self._anchor_grid_info.append({
          'level': level,
          'info': [scales, aspects, base_anchor_size, anchor_stride]
      })

  def name_scope(self):
    return 'MultiscaleGridAnchorGenerator'

  def num_anchors_per_location(self):
    """Returns the number of anchors per spatial location.

    Returns:
      a list of integers, one for each expected feature map to be passed to
      the Generate function.
    """
    return self._aspect_ratios * self._scales_per_octave

  def generate(self, feature_map_shape_list, im_height, im_width):
    """Generates a collection of bounding boxes to be used as anchors.

    Args:
      feature_map_shape_list: list of pairs of convnet layer resolutions in the
        format [(height_0, width_0), (height_1, width_1), ...]. For example,
        setting feature_map_shape_list=[(8, 8), (7, 7)] asks for anchors that
        correspond to an 8x8 layer followed by a 7x7 layer.
      im_height: the height of the image to generate the grid for.
      im_width: the width of the image to generate the grid for.

    Returns:
      boxes: a BoxList holding a collection of N anchor boxes
    """

    anchor_grid_list = []
    for feat_shape, grid_info in zip(feature_map_shape_list,
                                     self._anchor_grid_info):
      # TODO check the feature_map_shape_list is consistent with
      # self._anchor_grid_info
      level = grid_info['level']
      stride = 2**level
      scales, aspect_ratios, base_anchor_size, anchor_stride = grid_info['info']
      feat_h = feat_shape[0]
      feat_w = feat_shape[1]
      anchor_offset = [0, 0]
      if im_height % 2.0**level == 0:
        anchor_offset[0] = stride / 2.0
      if im_width % 2.0**level == 0:
        anchor_offset[1] = stride / 2.0
      ag = grid_anchor_generator.GridAnchorGenerator(
          scales,
          aspect_ratios,
          base_anchor_size=base_anchor_size,
          anchor_stride=anchor_stride,
          anchor_offset=anchor_offset)
      anchor_grid_list.append(
          ag.generate(feature_map_shape_list=[(feat_h, feat_w)]))

    concatenated_anchors = box_list_ops.concatenate(anchor_grid_list)

    return concatenated_anchors
