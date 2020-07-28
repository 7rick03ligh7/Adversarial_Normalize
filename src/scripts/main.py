import os
import sys
import random
import shutil

import pandas as pd
import pytorch_lightning as pl
from pytorch_lightning import loggers as pl_loggers
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint

from src.models.vgg_Like import VGGLike
import multiprocessing as mp
import argparse
import json
from src.utils.generates import *
from tqdm import tqdm


def worker(pid, queue, model_params):
    # if os.path.exists(model_params['logpath']):
    #     shutil.rmtree(model_params['logpath'])
    # os.makedirs(model_params['logpath'], exist_ok=True)

    model = VGGLike(model_params)
    tb_logger = pl_loggers.TensorBoardLogger(
        model_params['logdir'],
        name=model_params['logname'],
        version=''
        )
    os.makedirs(model_params['logpath']+'/checkpoints/best/', exist_ok=True)
    checkpoint_callback = ModelCheckpoint(
        filepath=model_params['logpath']+'/checkpoints/best/',
        save_top_k=1,
        verbose=False,
        monitor='val_acc',
        mode='max',
        prefix=''
    )
    trainer = Trainer(
        logger=tb_logger,
        checkpoint_callback=checkpoint_callback,
        max_epochs=100,
        num_sanity_val_steps=0,
        weights_summary=None,
        progress_bar_refresh_rate=0,
        track_grad_norm=1,
        gpus=[os.environ['CUDA_VISIBLE_DEVICES']]
        )
    trainer.fit(model)

def main_parallel(models_params):
    progress_bars = []
    processes = []
    progress_queue = mp.Queue()
    for i, model_params in enumerate(models_params):
        progress_bars.append(tqdm(total=model_params['epochs']))
        proc = mp.Process(target=worker, args=(i, progress_queue, model_params,))
        processes.append(proc)
        proc.start()

    while any([proc.is_alive() for proc in processes]):
        pid, status = progress_queue.get()
        if status:
            progress_bars[pid].update()
        if status == 9:
            processes[pid].join()

def main_debug(model_params):
    model_params = models_params[0]
    tb_logger = pl_loggers.TensorBoardLogger(
        model_params['logdir'],
        name=model_params['logname'],
        version=''
        )
    os.makedirs(model_params['logpath']+'/checkpoints/best/', exist_ok=True)
    checkpoint_callback = ModelCheckpoint(
        filepath=model_params['logpath']+'/checkpoints/best/',
        save_top_k=1,
        verbose=False,
        monitor='val_acc',
        mode='max',
        prefix=''
    )
    trainer = Trainer(
        logger=tb_logger,
        checkpoint_callback=checkpoint_callback,
        max_epochs=100,
        num_sanity_val_steps=0,
        weights_summary=None,
        progress_bar_refresh_rate=0,
        track_grad_norm=1,
        gpus=[os.environ['CUDA_VISIBLE_DEVICES']]
        )
    trainer.fit(model)


if __name__ == '__main__':
    mp.set_start_method('spawn')

    parser = argparse.ArgumentParser()
    parser.add_argument('--logdir', type=str, required=True)
    parser.add_argument('--params_file', type=str, required=True)
    parser.add_argument('--epochs', type=int, required=True)
    parser.add_argument('--seed', type=int, default=42, required=False)
    parser.add_argument('--debug', type=bool, default=False)
    arguments = parser.parse_args()

    with open(arguments.params_file, 'r') as f:
        models_params = json.load(f)

    for model_params in models_params:
        model_params['classes'] = [
            'airplane',
            'automobile',
            'bird',
            'cat',
            'deer',
            'dog',
            'frog',
            'horse',
            'ship',
            'truck'
        ]
        logname = generate_logname(model_params)
        logpath = './' + model_params['logdir'] + '/' + logname
        model_params['logname'] = logname
        model_params['logpath'] = logpath
        model_params['seed'] = arguments.seed
        model_params['epochs'] = arguments.epochs

    if arguments.debug:
        main
    else:
        main(models_params)

