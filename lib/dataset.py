import os
import random

import numpy as np
import torch
import torch.utils.data
from tqdm import tqdm

try:
    from lib import spec_utils
except ModuleNotFoundError:
    import spec_utils


class VocalRemoverTrainingSet(torch.utils.data.Dataset):

    def __init__(
            self, training_set, cropsize, reduction_rate, reduction_weight,
            mixup_rate, mixup_alpha, is_complex=False):
        self.training_set = training_set
        self.cropsize = cropsize
        self.reduction_rate = reduction_rate
        self.reduction_weight = reduction_weight
        self.mixup_rate = mixup_rate
        self.mixup_alpha = mixup_alpha
        self.is_complex = is_complex

    def __len__(self):
        return len(self.training_set)

    def read_npy_shape(self, path):
        with open(path, 'rb') as fhandle:
            _, _ = np.lib.format.read_magic(fhandle)
            shape, _, _ = np.lib.format.read_array_header_1_0(fhandle)
            return shape

    def read_npy_chunk(self, path, start_row):
        with open(path, 'rb') as fhandle:
            _, _ = np.lib.format.read_magic(fhandle)
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)

            assert not fortran, 'Fortran order arrays are not supported'

            row_size = np.prod(shape[1:])
            start_byte = start_row * row_size * dtype.itemsize
            fhandle.seek(start_byte, 1)
            n_items = row_size * self.cropsize
            flat = np.fromfile(fhandle, count=n_items, dtype=dtype)

            return flat.reshape((-1,) + shape[1:])

    def aggressively_remove_vocal(self, X, y):
        X_mag = np.abs(X)
        y_mag = np.abs(y)
        v_mag = X_mag - y_mag
        v_mag *= v_mag > y_mag

        y_mag = np.clip(y_mag - v_mag * self.reduction_weight, 0, np.inf)

        return y_mag * np.exp(1.j * np.angle(y))

    def do_crop(self, X_path, y_path, v_path):
        shape = self.read_npy_shape(X_path)
        start_row = np.random.randint(0, shape[0] - self.cropsize)

        X_crop = self.read_npy_chunk(X_path, start_row).transpose(1, 2, 0)
        y_crop = self.read_npy_chunk(y_path, start_row).transpose(1, 2, 0)
        v_crop = self.read_npy_chunk(v_path, start_row).transpose(1, 2, 0)

        return X_crop, y_crop, v_crop

    def do_aug(self, X, y, v):
        if np.random.uniform() < self.reduction_rate:
            y = self.aggressively_remove_vocal(X, y)

        if np.random.uniform() < 0.5:
            # swap channel
            X = X[::-1].copy()
            y = y[::-1].copy()
            v = v[::-1].copy()

        if np.random.uniform() < 0.01:
            # inst
            X = y.copy()
            v = np.zeros_like(X)

        # if np.random.uniform() < 0.01:
        #     # mono
        #     X[:] = X.mean(axis=0, keepdims=True)
        #     y[:] = y.mean(axis=0, keepdims=True)

        return X, y, v

    def do_mixup(self, X, y, v):
        idx = np.random.randint(0, len(self))
        X_path, y_path, v_path, coef = self.training_set[idx]

        X_i, y_i, v_i = self.do_crop(X_path, y_path, v_path)
        X_i /= coef
        y_i /= coef
        v_i /= coef

        X_i, y_i, v_i = self.do_aug(X_i, y_i, v_i)

        lam = np.random.beta(self.mixup_alpha, self.mixup_alpha)
        X = lam * X + (1 - lam) * X_i
        y = lam * y + (1 - lam) * y_i
        v = lam * v + (1 - lam) * v_i

        return X, y, v

    def __getitem__(self, idx):
        X_path, y_path, v_path, coef = self.training_set[idx]

        X, y, v = self.do_crop(X_path, y_path, v_path)
        X /= coef
        y /= coef
        v /= coef

        X, y, v = self.do_aug(X, y, v)

        if np.random.uniform() < self.mixup_rate:
            X, y, v = self.do_mixup(X, y, v)

        if self.is_complex:
            y = np.concatenate([y, v])
            return X, y
        else:
            X_mag = np.abs(X)
            y_mag = np.abs(np.concatenate([y, v]))
            return X_mag, y_mag


class VocalRemoverValidationSet(torch.utils.data.Dataset):

    def __init__(self, validation_set, is_complex=False):
        self.validation_set = validation_set
        self.is_complex = is_complex

    def __len__(self):
        return len(self.validation_set)

    def __getitem__(self, idx):
        path = self.validation_set[idx]
        data = np.load(path)

        X, y, v = data['X'], data['y'], data['v']

        if self.is_complex:
            y = np.concatenate([y, v])
            return X, y
        else:
            X_mag = np.abs(X)
            y_mag = np.abs(np.concatenate([y, v]))
            return X_mag, y_mag


def make_pair(X_dir, y_dir, v_dir=None):
    input_exts = ['.wav', '.m4a', '.mp3', '.mp4', '.flac']

    X_list = sorted([
        os.path.join(X_dir, fname)
        for fname in os.listdir(X_dir)
        if os.path.splitext(fname)[1] in input_exts
    ])
    y_list = sorted([
        os.path.join(y_dir, fname)
        for fname in os.listdir(y_dir)
        if os.path.splitext(fname)[1] in input_exts
    ])

    if v_dir is not None:
        v_list = sorted([
            os.path.join(v_dir, fname)
            for fname in os.listdir(v_dir)
            if os.path.splitext(fname)[1] in input_exts
        ])
        filelist = list(zip(X_list, y_list, v_list))
    else:
        filelist = list(zip(X_list, y_list))

    return filelist


def train_val_split(dataset_dir, split_mode, val_rate, val_filelist=[]):
    if split_mode == 'random':
        filelist = make_pair(
            os.path.join(dataset_dir, 'mixtures'),
            os.path.join(dataset_dir, 'instruments'),
            os.path.join(dataset_dir, 'pseudo_vocals')
        )

        random.shuffle(filelist)

        if len(val_filelist) == 0:
            val_size = int(len(filelist) * val_rate)
            train_filelist = filelist[:-val_size]
            val_filelist = filelist[-val_size:]
        else:
            train_filelist = [
                pair for pair in filelist
                if list(pair) not in val_filelist
            ]
    elif split_mode == 'subdirs':
        if len(val_filelist) != 0:
            raise ValueError('`val_filelist` option is not available with `subdirs` mode')

        train_filelist = make_pair(
            os.path.join(dataset_dir, 'training/mixtures'),
            os.path.join(dataset_dir, 'training/instruments'),
            os.path.join(dataset_dir, 'training/pseudo_vocals')
        )

        val_filelist = make_pair(
            os.path.join(dataset_dir, 'validation/mixtures'),
            os.path.join(dataset_dir, 'validation/instruments'),
            os.path.join(dataset_dir, 'validation/pseudo_vocals')
        )

    return train_filelist, val_filelist


def raw_data_split(dataset_dir, split_mode):
    if split_mode == 'random':
        filelist = make_pair(
            os.path.join(dataset_dir, 'mixtures'),
            os.path.join(dataset_dir, 'instruments'),
        )
    elif split_mode == 'subdirs':
        train_filelist = make_pair(
            os.path.join(dataset_dir, 'training/mixtures'),
            os.path.join(dataset_dir, 'training/instruments'),
        )
        val_filelist = make_pair(
            os.path.join(dataset_dir, 'validation/mixtures'),
            os.path.join(dataset_dir, 'validation/instruments'),
        )
        filelist = train_filelist + val_filelist

    return filelist


def make_padding(width, cropsize, offset):
    left = offset
    roi_size = cropsize - offset * 2
    if roi_size == 0:
        roi_size = cropsize
    right = roi_size - (width % roi_size) + left

    return left, right, roi_size


def make_training_set(filelist, sr, hop_length, n_fft):
    ret = []
    for X_path, y_path, v_path in tqdm(filelist):
        X, y, v, X_cache_path, y_cache_path, v_cache_path = spec_utils.cache_or_load(
            X_path, y_path, v_path, sr, hop_length, n_fft
        )
        coef = np.max([np.abs(X).max(), np.abs(y).max(), np.abs(v).max()])
        ret.append([X_cache_path, y_cache_path, v_cache_path, coef])

    return ret


def make_validation_set(filelist, cropsize, sr, hop_length, n_fft, offset):
    patch_list = []
    patch_dir = 'cs{}_sr{}_hl{}_nf{}_of{}'.format(cropsize, sr, hop_length, n_fft, offset)
    os.makedirs(patch_dir, exist_ok=True)

    for X_path, y_path, v_path in tqdm(filelist):
        basename = os.path.splitext(os.path.basename(X_path))[0]

        X, y, v, _, _, _ = spec_utils.cache_or_load(X_path, y_path, v_path, sr, hop_length, n_fft)
        coef = np.max([np.abs(X).max(), np.abs(y).max(), np.abs(v).max()])
        X, y, v = X / coef, y / coef, v / coef

        l, r, roi_size = make_padding(X.shape[2], cropsize, offset)
        X_pad = np.pad(X, ((0, 0), (0, 0), (l, r)), mode='constant')
        y_pad = np.pad(y, ((0, 0), (0, 0), (l, r)), mode='constant')
        v_pad = np.pad(v, ((0, 0), (0, 0), (l, r)), mode='constant')

        len_dataset = int(np.ceil(X.shape[2] / roi_size))
        for j in range(len_dataset):
            outpath = os.path.join(patch_dir, '{}_p{}.npz'.format(basename, j))
            start = j * roi_size
            if not os.path.exists(outpath):
                np.savez(
                    outpath,
                    X=X_pad[:, :, start:start + cropsize],
                    y=y_pad[:, :, start:start + cropsize],
                    v=v_pad[:, :, start:start + cropsize]
                )
            patch_list.append(outpath)

    return patch_list


if __name__ == "__main__":
    import sys
    import utils

    mix_dir = sys.argv[1]
    inst_dir = sys.argv[2]
    outdir = sys.argv[3]

    os.makedirs(outdir, exist_ok=True)

    filelist = make_pair(mix_dir, inst_dir)
    for mix_path, inst_path in tqdm(filelist):
        mix_basename = os.path.splitext(os.path.basename(mix_path))[0]

        X_spec, y_spec, _, _ = spec_utils.cache_or_load(
            mix_path, inst_path, 44100, 1024, 2048
        )

        X_mag = np.abs(X_spec)
        y_mag = np.abs(y_spec)
        v_mag = X_mag - y_mag
        v_mag *= v_mag > y_mag

        outpath = '{}/{}_Vocal.jpg'.format(outdir, mix_basename)
        v_image = spec_utils.spectrogram_to_image(v_mag)
        utils.imwrite(outpath, v_image)
