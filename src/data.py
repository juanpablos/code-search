import pickle
import random

import numpy as np
import tables
import torch
import torch.utils.data as data

use_cuda = torch.cuda.is_available()

PAD_token = 0
SOS_token = 1
EOS_token = 2
UNK_token = 3


class CodeSearchDataset(data.Dataset):
    """
    Dataset that has only positive samples.
    """

    def __init__(self, data_dir, f_name, name_len, f_api, api_len,
                 f_tokens, tok_len, f_descs=None, desc_len=None):
        self.name_len = name_len
        self.api_len = api_len
        self.tok_len = tok_len
        self.desc_len = desc_len
        # 1. Initialize file path or list of file names.
        """read training data(list of int arrays) from a hdf5 file"""
        self.training = False
        print("loading data...")
        table_name = tables.open_file(data_dir + f_name)
        self.names = table_name.get_node('/phrases')
        self.idx_names = table_name.get_node('/indices')
        table_api = tables.open_file(data_dir + f_api)
        self.apis = table_api.get_node('/phrases')
        self.idx_apis = table_api.get_node('/indices')
        table_tokens = tables.open_file(data_dir + f_tokens)
        self.tokens = table_tokens.get_node('/phrases')
        self.idx_tokens = table_tokens.get_node('/indices')
        if f_descs is not None:
            self.training = True
            table_desc = tables.open_file(data_dir + f_descs)
            self.descs = table_desc.get_node('/phrases')
            self.idx_descs = table_desc.get_node('/indices')

        assert self.idx_names.shape[0] == self.idx_apis.shape[0]
        assert self.idx_apis.shape[0] == self.idx_tokens.shape[0]
        if f_descs is not None:
            assert self.idx_names.shape[0] == self.idx_descs.shape[0]
        self.data_len = self.idx_names.shape[0]
        print("{} entries".format(self.data_len))

    def pad_seq(self, seq, maxlen):
        if len(seq) < maxlen:
            seq = np.append(seq, [PAD_token] * maxlen)
            seq = seq[:maxlen]
        else:
            seq = seq[:maxlen]
        return seq

    def __getitem__(self, offset):
        length, pos = self.idx_names[offset]['length'], self.idx_names[offset]['pos']
        name = self.names[pos:pos + length].astype('int64')
        name = self.pad_seq(name, self.name_len)

        length, pos = self.idx_apis[offset]['length'], self.idx_apis[offset]['pos']
        apiseq = self.apis[pos:pos + length].astype('int64')
        apiseq = self.pad_seq(apiseq, self.api_len)

        length, pos = self.idx_tokens[offset]['length'], self.idx_tokens[offset]['pos']
        tokens = self.tokens[pos:pos + length].astype('int64')
        tokens = self.pad_seq(tokens, self.tok_len)

        if self.training:
            length, pos = self.idx_descs[offset]['length'], self.idx_descs[offset]['pos']
            good_desc = self.descs[pos:pos + length].astype('int64')
            good_desc = self.pad_seq(good_desc, self.desc_len)

            rand_offset = random.randint(0, self.data_len - 1)
            length, pos = self.idx_descs[rand_offset]['length'], self.idx_descs[rand_offset]['pos']
            bad_desc = self.descs[pos:pos + length].astype('int64')
            bad_desc = self.pad_seq(bad_desc, self.desc_len)

            return name, apiseq, tokens, good_desc, bad_desc
        else:
            return name, apiseq, tokens

    def __len__(self):
        return self.data_len


def load_dict(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def load_vecs(fin):
    """read vectors (2D numpy array) from a hdf5 file"""
    with tables.open_file(fin) as h5f:
        return np.array(h5f.root.vecs)


def save_vecs(vecs, fout):
    with tables.open_file(fout, 'w') as fvec:
        atom = tables.Atom.from_dtype(vecs.dtype)
        filters = tables.Filters(complib='blosc', complevel=5)
        ds = fvec.create_carray(fvec.root, 'vecs', atom, vecs.shape, filters=filters)
        ds[:] = vecs
        print('done')
