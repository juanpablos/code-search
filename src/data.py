import pickle
import random
import re
import subprocess
from ast import literal_eval

import jnius_config
import lmdb
import numpy as np
import tables
import torch
import torch.utils.data as data

jnius_config.set_classpath('./*')

from jnius import autoclass

use_cuda = torch.cuda.is_available()

PAD_token = 0
# SOS_token = 1
# EOS_token = 2
UNK_token = 1


class CodeSearchDataset(data.Dataset):
    """
    Dataset that has only positive samples.
    """

    def __init__(self, db, name_voc, name_len, api_voc, api_len,
                 token_voc, token_len, desc_voc=None, desc_len=None):
        """

        :param db: db containing the comments and codes
        :param name_voc: mapping with word-identifier
        :param name_len: max length of a name
        :param api_voc: mapping with word-identifier
        :param api_len: max length of an api sequence
        :param token_voc: mapping with word-identifier
        :param token_len: max length of a set of tokens
        :param desc_voc: mapping with word-identifier
        :param desc_len: max length of a comment
        """

        self.name_len = name_len
        self.api_len = api_len
        self.token_len = token_len
        self.desc_len = desc_len

        self.name_voc = name_voc
        self.api_voc = api_voc
        self.token_voc = token_voc

        if desc_voc is not None:
            self.training = True
            self.desc_voc = desc_voc

        self.data = lmdb.open(db, readonly=True)

        self.parser = autoclass('parser.MethodCodeParser')()

        with self.data.begin() as txn:
            self.data_len = txn.stat()['entries']

        print("{} entries".format(self.data_len))

    def pad_seq(self, seq, maxlen):
        if len(seq) < maxlen:
            seq = np.append(seq, [PAD_token] * maxlen)
            seq = seq[:maxlen]
        else:
            seq = seq[:maxlen]
        return seq

    def __getitem__(self, offset):
        with self.data.begin(write=False) as txn:
            method_bytes = txn.get('{:09}'.format(offset).encode('ascii'))
            comment, method = pickle.loads(method_bytes)

        container = literal_eval(
            subprocess.check_output(["java", "-jar", "JavaParser.jar", "{}".format(method)]).decode('utf-8').strip())
        
        name = [self.name_voc.get(_name, UNK_token) for _name in container["name"]]
        apiseq = [self.api_voc.get(_api, UNK_token) for _api in container["api"]]
        tokens = [self.token_voc.get(_token, UNK_token) for _token in container["token"]]

        name = self.pad_seq(name, self.name_len)
        apiseq = self.pad_seq(apiseq, self.api_len)
        tokens = self.pad_seq(tokens, self.token_len)

        if self.training:

            good_desc = [self.desc_voc.get(word, UNK_token) for word in re.findall(r"[\w]+", comment.lower())]
            good_desc = self.pad_seq(good_desc, self.desc_len)

            rand_offset = random.randint(0, self.data_len - 1)
            with self.data.begin(write=False) as txn:
                method_bytes = txn.get('{:09}'.format(rand_offset).encode('ascii'))
                bad_comment, _ = pickle.loads(method_bytes)

            bad_desc = [self.desc_voc.get(word, UNK_token) for word in re.findall(r"[\w]+", bad_comment.lower())]
            bad_desc = self.pad_seq(bad_desc, self.desc_len)

            return name, apiseq, tokens, good_desc, bad_desc
        else:
            return name, apiseq, tokens

    def __len__(self):
        return self.data_len


def load_dict(filename, max_vocab):
    with open(filename, 'rb') as f:
        vocab = pickle.load(f)[:max_vocab + 1]  # pandas DataFrame
        return dict(zip(vocab.iloc[:, 0], vocab.iloc[:, 1]))


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
