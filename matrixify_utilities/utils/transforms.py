# ------------------------------------------------------------------------------
# Copyright (c) Microsoft
# Licensed under the MIT License.
# Written by Bin Xiao (Bin.Xiao@microsoft.com)
# ------------------------------------------------------------------------------

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import cv2
import torch

class BRG2Tensor_transform(object):
    def __call__(self, pic):
        img = torch.from_numpy(pic.transpose((2, 0, 1)))
        if isinstance(img, torch.ByteTensor):
            return img.float()
        else:
            return img

class BGR2RGB_transform(object):
    def __call__(self, tensor):
        return tensor[[2,1,0],:,:]

def flip_back(output_flipped, matched_parts):
    '''
    ouput_flipped: numpy.ndarray(batch_size, num_joints, height, width)
    '''
    assert output_flipped.ndim == 4,\
        'output_flipped should be [batch_size, num_joints, height, width]'

    output_flipped = output_flipped[:, :, :, ::-1]

    for pair in matched_parts:
        tmp = output_flipped[:, pair[0], :, :].copy()
        output_flipped[:, pair[0], :, :] = output_flipped[:, pair[1], :, :]
        output_flipped[:, pair[1], :, :] = tmp

    return output_flipped


def fliplr_joints(joints, joints_vis, width, matched_parts):
    """
    flip coords
    """
    # Flip horizontal
    joints[:, 0] = width - joints[:, 0] - 1

    # Change left-right parts
    for pair in matched_parts:
        joints[pair[0], :], joints[pair[1], :] = \
            joints[pair[1], :], joints[pair[0], :].copy()
        joints_vis[pair[0], :], joints_vis[pair[1], :] = \
            joints_vis[pair[1], :], joints_vis[pair[0], :].copy()

    return joints*joints_vis, joints_vis


def transform_preds(coords, center, scale, input_size):
    target_coords = np.zeros(coords.shape)
    trans = get_affine_transform(center, scale, 0, input_size, inv=1)
    for p in range(coords.shape[0]):
        target_coords[p, 0:2] = affine_transform(coords[p, 0:2], trans)
    return target_coords

def transform_parsing(pred, center, scale, width, height, input_size):
    """Transform parsing result to original image size using direct resize."""
    # Simple resize to target dimensions
    target_pred = cv2.resize(
        pred,
        (width, height),
        interpolation=cv2.INTER_NEAREST  # Use NEAREST for label maps
    )
    
    return target_pred

def transform_logits(logits, center, scale, width, height, input_size):
    """Transform logits according to image original size."""
    if isinstance(input_size, list):
        input_size = input_size
    else:
        input_size = [input_size, input_size]
    
    # Get transform matrix
    trans = get_affine_transform(center, scale, 0, (height, width), inv=1)
    
    # Transform each channel
    channel = logits.shape[2]
    target_logits = []
    
    print(f"\nLogits Transform Debug:")
    print(f"Input shape: {logits.shape}")
    print(f"Target size: ({height}, {width})")
    
    for i in range(channel):
        target_logit = cv2.resize(
            logits[:, :, i],
            (width, height),
            interpolation=cv2.INTER_LINEAR
        )
        target_logits.append(target_logit)
    
    # Stack channels
    target_logits = np.stack(target_logits, axis=2)
    
    return target_logits


def get_affine_transform(center,
                        scale,
                        rot,
                        output_size,
                        shift=np.array([0, 0], dtype=np.float32),
                        inv=0):
    """Get affine transform matrix."""
    if not isinstance(scale, np.ndarray) and not isinstance(scale, list):
        scale = np.array([scale, scale])

    # Ensure output_size is [height, width]
    if not isinstance(output_size, (list, tuple, np.ndarray)):
        output_size = [output_size, output_size]
    output_size = np.array(output_size)
    
    # Simple scaling factors
    scale_x = output_size[1] / scale[0]  # width scaling
    scale_y = output_size[0] / scale[1]  # height scaling
    
    # Create transformation matrix
    trans = np.array([
        [scale_x, 0, 0],
        [0, scale_y, 0]
    ], dtype=np.float32)
    
    # Debug output
    print("\nTransform Debug:")
    print(f"Input dimensions: {scale}")
    print(f"Output dimensions: {output_size}")
    print(f"Scale factors: x={scale_x:.3f}, y={scale_y:.3f}")
    print(f"Transform matrix:\n{trans}")
    
    if inv:
        # For inverse transform, invert the scale factors
        trans = np.array([
            [1/scale_x, 0, 0],
            [0, 1/scale_y, 0]
        ], dtype=np.float32)
    
    return trans


def affine_transform(pt, t):
    new_pt = np.array([pt[0], pt[1], 1.]).T
    new_pt = np.dot(t, new_pt)
    return new_pt[:2]


def get_3rd_point(a, b):
    direct = a - b
    return b + np.array([-direct[1], direct[0]], dtype=np.float32)


def get_dir(src_point, rot_rad):
    sn, cs = np.sin(rot_rad), np.cos(rot_rad)

    src_result = [0, 0]
    src_result[0] = src_point[0] * cs - src_point[1] * sn
    src_result[1] = src_point[0] * sn + src_point[1] * cs

    return src_result


def crop(img, center, scale, output_size, rot=0):
    trans = get_affine_transform(center, scale, rot, output_size)

    dst_img = cv2.warpAffine(img,
                             trans,
                             (int(output_size[1]), int(output_size[0])),
                             flags=cv2.INTER_LINEAR)

    return dst_img
