#!/usr/bin/env python
# --------------------------------------------------------------------------------
# MPViT: Multi-Path Vision Transformer for Dense Prediction
# Copyright (c) 2022 Electronics and Telecommunications Research Institute (ETRI).
# All Rights Reserved.
# Written by Youngwan Lee
# --------------------------------------------------------------------------------

"""
Detection Training Script for MPViT.
"""

import os
import itertools

import torch

from typing import Any, Dict, List, Set

from detectron2.data import build_detection_train_loader
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer, default_argument_parser, default_setup, launch
from detectron2.evaluation import COCOEvaluator
from detectron2.solver.build import maybe_add_gradient_clipping

from ditod import add_vit_config
from ditod import DetrDatasetMapper

from detectron2.data.datasets import register_coco_instances
import logging
from detectron2.utils.logger import setup_logger
from detectron2.utils import comm
from detectron2.engine.defaults import create_ddp_model
import weakref
from detectron2.engine.train_loop import AMPTrainer, SimpleTrainer
from ditod import MyDetectionCheckpointer, ICDAREvaluator
from ditod import MyTrainer


def setup(args):
    """
    Create configs and perform basic setups.
    """
    cfg = get_cfg()
    # add_coat_config(cfg)
    add_vit_config(cfg)
    cfg.merge_from_file(args.config_file)
    cfg.DATASETS.TRAIN = (args.train_dataset,)
    cfg.DATASETS.TEST = (args.test_dataset,)
    cfg.merge_from_list(args.opts)
    cfg.freeze()
    default_setup(cfg, args)
    return cfg


def main(args):
    """
    register publaynet first
    """
    register_coco_instances(
        args.train_dataset,
        {},
        args.train_json,
        args.train_images
    )

    register_coco_instances(
        args.val_dataset,
        {},
        args.val_json,
        args.val_images
    )

    cfg = setup(args)

    if args.eval_only:
        model = MyTrainer.build_model(cfg)
        DetectionCheckpointer(model, save_dir=cfg.OUTPUT_DIR).resume_or_load(
            cfg.MODEL.WEIGHTS, resume=args.resume
        )
        res = MyTrainer.test(cfg, model)
        return res

    trainer = MyTrainer(cfg)
    trainer.resume_or_load(resume=args.resume)
    return trainer.train()


if __name__ == "__main__":
    parser = default_argument_parser()
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    parser.add_argument("--train_dataset", help="Train dataset name", default="data_train")
    parser.add_argument("--val_dataset", help="Test dataset name", default="data_val")
    parser.add_argument("--train_json", help="Training JSON")
    parser.add_argument("--train_images", help="Training images directory")
    parser.add_argument("--val_json", help="Validation JSON")
    parser.add_argument("--val_images", help="Validation images directory")
    args = parser.parse_args()
    print("Command Line Args:", args)

    if args.debug:
        import debugpy

        print("Enabling attach starts.")
        debugpy.listen(address=('0.0.0.0', 9310))
        debugpy.wait_for_client()
        print("Enabling attach ends.")

    launch(
        main,
        args.num_gpus,
        num_machines=args.num_machines,
        machine_rank=args.machine_rank,
        dist_url=args.dist_url,
        args=(args,),
    )
