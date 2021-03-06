#! /usr/bin/env python
# coding=utf-8
#================================================================
#   Copyright (C) 2019 * Ltd. All rights reserved.
#
#   Editor      : VIM
#   File name   : utils.py
#   Author      : YunYang1994
#   Created date: 2019-02-28 13:14:19
#   Description :
#
#================================================================

import cv2
import random
import colorsys
import numpy as np
import tensorflow as tf
# from config import cfg
# np.set_printoptions(linewidth=1000,edgeitems=500,suppress=True)
import torch

def warm_up_lr(global_step, warmup_steps, learn_rate_init):
    return global_step / warmup_steps* learn_rate_init

def read_class_names(class_file_name):
    '''loads class name from a file'''
    names = {}
    with open(class_file_name, 'r') as data:
        for ID, name in enumerate(data):
            names[ID] = name.strip('\n')
        # print("names",names)
    return names


def get_anchors(anchors_path):
    '''loads the anchors from a file'''
    with open(anchors_path) as f:
        anchors = f.readline()
    anchors = np.array(anchors.split(','), dtype=np.float32)
    # print("anchors.reshape((3, 3, 2))",anchors.reshape((3, 3, 2)))
    return anchors.reshape((3, 3, 2))


def image_preporcess(bgr_image, target_size, gt_boxes=None):   # 转化为416*416的图片
    # cv2.imshow("img3", bgr_image)
    # cv2.imwrite("./3.jpg", bgr_image)
    # cv2.waitKey(0)
    bgr_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB).astype(np.float32)

    ih, iw    = target_size
    # print("target_size",target_size)     #ih, iw = 416
    h,  w, _  = bgr_image.shape
    # print("22bgr_image.shape",bgr_image.shape)
    scale = min(iw/w, ih/h)
    # print("221scale",scale)
    nw, nh  = int(scale * w), int(scale * h)
    # print("23(nw, nh)", nw, nh)     # bgr_image.shape 原图片尺寸，nw=416,nh = 289
    image_resized = cv2.resize(bgr_image, (nw, nh))
    # print("24image_resized",image_resized.shape)  # image_resized有值，是具体图片的像素值

    image_paded = np.full(shape=[ih, iw, 3], fill_value=128.0)
    # print("25image_paded ",image_paded,image_paded.shape)   # 全是128,416*416*3
    dw, dh = (iw - nw) // 2, (ih-nh) // 2
    # print("26dw, dh",dw, dh)
    # print("27修改像素值",nh,dh,nw,dw)
    image_paded[dh:nh+dh, dw:nw+dw, :] = image_resized
    # print("image_paded",image_paded.shape)
    # img12 = np.array(image_paded).astype(np.uint8)
    # cv2.imshow("img4", img12)
    # cv2.imwrite("./4.jpg", img12)
    # cv2.waitKey(0)

    image_paded = image_paded / 255.


    if gt_boxes is None:
        return image_paded
    else:
        gt_boxes[:, [0, 2]] = gt_boxes[:, [0, 2]] * scale + dw
        gt_boxes[:, [1, 3]] = gt_boxes[:, [1, 3]] * scale + dh

        return image_paded, gt_boxes

path1 = r"./data/classes/antenna.names"

def draw_bbox(image, bboxes, classes=read_class_names(path1), show_label=True):
    """
    bboxes: [x_min, y_min, x_max, y_max, probability, cls_id] format coordinates.
    """

    num_classes = len(classes)
    image_h, image_w, _ = image.shape
    hsv_tuples = [(1.0 * x / num_classes, 1., 1.) for x in range(num_classes)]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)), colors))

    random.seed(0)
    random.shuffle(colors)
    random.seed(None)



    for i, bbox in enumerate(bboxes):
        coor = np.array(bbox[:4], dtype=np.int32)
        fontScale1 = 1
        fontScale2 = 0.6

        score = bbox[4]
        class_ind = int(bbox[5])

        bbox_color = colors[class_ind]
        bbox_thick = 2
        c1, c2 = (coor[0], coor[1]), (coor[2], coor[3])
        cv2.rectangle(image, c1, c2, bbox_color, bbox_thick)

        if show_label:
            if image_h>1000 or image_w>1000:
                bbox_mess = '%s: %.2f: %s' % (classes[class_ind], score,i)
                t_size = cv2.getTextSize(bbox_mess, 0, fontScale1, thickness=bbox_thick//2)[0]
                cv2.rectangle(image, c1, (c1[0] + t_size[0], c1[1] - t_size[1] - 3), bbox_color, -1)  # filled
                cv2.putText(image, bbox_mess, (c1[0], c1[1]-2), cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale1, (0, 0, 0), bbox_thick//2, lineType=cv2.LINE_AA)
            else:
                bbox_mess = '%s: %.2f' % (classes[class_ind], score)
                t_size = cv2.getTextSize(bbox_mess, 0, fontScale2, thickness=bbox_thick // 2)[0]
                cv2.rectangle(image, c1, (c1[0] + t_size[0], c1[1] - t_size[1] - 3), bbox_color, -1)  # filled
                cv2.putText(image, bbox_mess, (c1[0], c1[1] - 2), cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale2, (0, 0, 0), bbox_thick // 2, lineType=cv2.LINE_AA)
    return image



def bboxes_iou(boxes1, boxes2):

    boxes1 = np.array(boxes1)
    boxes2 = np.array(boxes2)

    boxes1_area = (boxes1[..., 2] - boxes1[..., 0]) * (boxes1[..., 3] - boxes1[..., 1])
    boxes2_area = (boxes2[..., 2] - boxes2[..., 0]) * (boxes2[..., 3] - boxes2[..., 1])

    left_up       = np.maximum(boxes1[..., :2], boxes2[..., :2])
    right_down    = np.minimum(boxes1[..., 2:], boxes2[..., 2:])

    inter_section = np.maximum(right_down - left_up, 0.0)
    inter_area    = inter_section[..., 0] * inter_section[..., 1]
    union_area    = boxes1_area + boxes2_area - inter_area
    ious          = np.maximum(1.0 * inter_area / union_area, np.finfo(np.float32).eps)

    return ious



def read_pb_return_tensors(graph, pb_file, return_elements):

    with tf.gfile.FastGFile(pb_file, 'rb') as f:
        frozen_graph_def = tf.GraphDef()
        frozen_graph_def.ParseFromString(f.read())

    with graph.as_default():
        return_elements = tf.import_graph_def(frozen_graph_def,
                                              return_elements=return_elements)
    return return_elements


def nms(bboxes, iou_threshold, sigma=0.3, method='nms'):
    """
    :param bboxes: (xmin, ymin, xmax, ymax, score, class)

    Note: soft-nms, https://arxiv.org/pdf/1704.04503.pdf
          https://github.com/bharatsingh430/soft-nms
    """
    classes_in_img = list(set(bboxes[:, 5]))
    best_bboxes = []

    for cls in classes_in_img:
        cls_mask = (bboxes[:, 5] == cls)
        cls_bboxes = bboxes[cls_mask]

        while len(cls_bboxes) > 0:
            max_ind = np.argmax(cls_bboxes[:, 4])
            best_bbox = cls_bboxes[max_ind]
            best_bboxes.append(best_bbox)
            cls_bboxes = np.concatenate([cls_bboxes[: max_ind], cls_bboxes[max_ind + 1:]])
            iou = bboxes_iou(best_bbox[np.newaxis, :4], cls_bboxes[:, :4])
            weight = np.ones((len(iou),), dtype=np.float32)

            assert method in ['nms', 'soft-nms']

            if method == 'nms':
                iou_mask = iou > iou_threshold
                weight[iou_mask] = 0.0

            if method == 'soft-nms':
                weight = np.exp(-(1.0 * iou ** 2 / sigma))

            cls_bboxes[:, 4] = cls_bboxes[:, 4] * weight
            score_mask = cls_bboxes[:, 4] > 0.
            cls_bboxes = cls_bboxes[score_mask]

    return best_bboxes


def postprocess_boxes(pred_bbox, org_img_shape, input_size, score_threshold):

    valid_scale=[0, np.inf]
    pred_bbox = np.array(pred_bbox)

    pred_xywh = pred_bbox[:, 0:4]
    pred_conf = pred_bbox[:, 4]
    pred_prob = pred_bbox[:, 5:]

    # # (1) (x, y, w, h) --> (xmin, ymin, xmax, ymax)
    pred_coor = np.concatenate([pred_xywh[:, :2] - pred_xywh[:, 2:] * 0.5,
                                pred_xywh[:, :2] + pred_xywh[:, 2:] * 0.5], axis=-1)
    # # (2) (xmin, ymin, xmax, ymax) -> (xmin_org, ymin_org, xmax_org, ymax_org)
    org_h, org_w = org_img_shape
    resize_ratio = min(input_size / org_w, input_size / org_h)

    dw = (input_size - resize_ratio * org_w) / 2
    dh = (input_size - resize_ratio * org_h) / 2

    pred_coor[:, 0::2] = 1.0 * (pred_coor[:, 0::2] - dw) / resize_ratio
    pred_coor[:, 1::2] = 1.0 * (pred_coor[:, 1::2] - dh) / resize_ratio

    # # (3) clip some boxes those are out of range
    pred_coor = np.concatenate([np.maximum(pred_coor[:, :2], [0, 0]),
                                np.minimum(pred_coor[:, 2:], [org_w - 1, org_h - 1])], axis=-1)
    invalid_mask = np.logical_or((pred_coor[:, 0] > pred_coor[:, 2]), (pred_coor[:, 1] > pred_coor[:, 3]))
    pred_coor[invalid_mask] = 0

    # # (4) discard some invalid boxes
    bboxes_scale = np.sqrt(np.multiply.reduce(pred_coor[:, 2:4] - pred_coor[:, 0:2], axis=-1))
    scale_mask = np.logical_and((valid_scale[0] < bboxes_scale), (bboxes_scale < valid_scale[1]))

    # # (5) discard some boxes with low scores
    classes = np.argmax(pred_prob, axis=-1)
    scores = pred_conf * pred_prob[np.arange(len(pred_coor)), classes]

    print("utils268",np.max(scores))
    score_mask = scores > score_threshold
    mask = np.logical_and(scale_mask, score_mask)
    coors, scores, classes = pred_coor[mask], scores[mask], classes[mask]

    return np.concatenate([coors, scores[:, np.newaxis], classes[:, np.newaxis]], axis=-1)

def py_ious(box, boxes, isMin=False):
    box_area = (box[2] - box[0]) * (box[3] - box[1])
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    xx1 = torch.max(box[0], boxes[:, 0])
    yy1 = torch.max(box[1], boxes[:, 1])
    xx2 = torch.min(box[2], boxes[:, 2])
    yy2 = torch.min(box[3], boxes[:, 3])

    # w = torch.max(0, xx2 - xx1)
    # h = torch.max(0, yy2 - yy1)
    w = torch.clamp(xx2 - xx1, min=0)
    h = torch.clamp(yy2 - yy1, min=0)

    inter = w * h

    # ovr1 = inter/torch.min(box_area, area)
    ovr2 = inter / (box_area + area - inter)
    # ovr = torch.max(ovr2,ovr1)

    # if isMin:#用于判断是交集/并集，还是交集/最小面积（用于处理大框套小框的情况）
    #
    #     ovr = inter / torch.min(box_area, area)
    # else:
    #     ovr = inter / (box_area + area - inter)

    return ovr2


def py_nms(boxes, thresh=0.3, isMin=True):
    if boxes.shape[0] == 0:
        return np.array([])

    _boxes = boxes[(-boxes[:, 4]).argsort()]

    r_boxes = []

    while _boxes.shape[0] > 1:
        a_box = _boxes[0]
        b_boxes = _boxes[1:]
        r_boxes.append(a_box)
        # print(py_ious(a_box, b_boxes))
        index = np.where(py_ious(a_box, b_boxes, isMin) < thresh)
        _boxes = b_boxes[index]
    if _boxes.shape[0] > 0:
        r_boxes.append(_boxes[0])

    return torch.stack(r_boxes)


def draw_bbox2(image, bboxes,bolt_num, siam,classes=read_class_names(path1), show_label=True):
    """
    bboxes: [x_min, y_min, x_max, y_max, probability, cls_id] format coordinates.
    """

    num_classes = len(classes)
    image_h, image_w, _ = image.shape
    colors = [(0, 0, 255)]
    random.seed(0)
    random.shuffle(colors)
    random.seed(None)



    for i, bbox in enumerate(bboxes):
        coor = np.array(bbox[:4], dtype=np.int32)
        fontScale1 = 1
        fontScale2 = 0.6

        score = bbox[4]
        class_ind = int(bbox[5])
        print('class_ind',class_ind,colors,len(colors))
        bbox_color = colors[class_ind-1]
        print('bbox_color',bbox_color)
        bbox_thick = 2
        c1, c2 = (coor[0], coor[1]), (coor[2], coor[3])
        cv2.rectangle(image, c1, c2, bbox_color, bbox_thick)

        if show_label:
            if image_h>1000 or image_w>1000:
                print('classes[class_ind-1]',classes[0])
                print('bolt_num[i]',bolt_num[i])
                bbox_mess = '%s: %.2f: %s' % (classes[0], siam[i],bolt_num[i])
                t_size = cv2.getTextSize(bbox_mess, 0, fontScale1, thickness=bbox_thick//2)[0]
                cv2.rectangle(image, c1, (c1[0] + t_size[0], c1[1] - t_size[1] - 3), bbox_color, -1)  # filled
                cv2.putText(image, bbox_mess, (c1[0], c1[1]-2), cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale1, (0, 0, 0), bbox_thick//2, lineType=cv2.LINE_AA)
            else:
                bbox_mess = '%s: %.2f: %s' % (classes[0], siam[i],bolt_num[i])
                t_size = cv2.getTextSize(bbox_mess, 0, fontScale2, thickness=bbox_thick // 2)[0]
                cv2.rectangle(image, c1, (c1[0] + t_size[0], c1[1] - t_size[1] - 3), bbox_color, -1)  # filled
                cv2.putText(image, bbox_mess, (c1[0], c1[1] - 2), cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale2, (0, 0, 0), bbox_thick // 2, lineType=cv2.LINE_AA)
    return image

if __name__ == '__main__':
    bolt_path1 = r"./data/classes/bolt.names"
    classes = read_class_names(bolt_path1)
    print('name',classes)

    print('classes[class_ind-1]', classes[0],type(classes[0]))
