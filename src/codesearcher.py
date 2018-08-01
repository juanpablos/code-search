import argparse
import codecs
import logging
import math
import os
import random
import threading
import traceback

import numpy as np
import torch
import torch.nn.functional as F
from torch import optim

from configs import get_config
from data import load_dict, CodeSearchDataset, load_vecs, save_vecs
from models import JointEmbeder
from utils import normalize, dot_np, gVar, sent2indexes

random.seed(42)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


class CodeSearcher:
    def __init__(self, conf):
        self.model_params = conf
        self.path = conf['workdir']

        self.vocab_methname = load_dict(self.path + conf['vocab_name'])
        self.vocab_apiseq = load_dict(self.path + conf['vocab_api'])
        self.vocab_tokens = load_dict(self.path + conf['vocab_tokens'])
        self.vocab_desc = load_dict(self.path + conf['vocab_desc'])

        self.codevecs = []
        self.codebase = []
        self.codebase_chunksize = 2000000

    # Data Set
    def load_codebase(self):
        """load codebase
        codefile: h5 file that stores raw code
        """
        logger.info('Loading codebase (chunk size={})..'.format(self.codebase_chunksize))
        if not self.codebase:  # empty
            codes = codecs.open(self.path + self.model_params['use_codebase']).readlines()
            # use codecs to read in case of encoding problem
            for i in range(0, len(codes), self.codebase_chunksize):
                self.codebase.append(codes[i:i + self.codebase_chunksize])

    # Results Data
    def load_codevecs(self):
        logger.debug('Loading code vectors..')
        if not self.codevecs:  # empty
            """read vectors (2D numpy array) from a hdf5 file"""
            reprs = load_vecs(self.path + self.model_params['use_codevecs'])
            for i in range(0, reprs.shape[0], self.codebase_chunksize):
                self.codevecs.append(reprs[i:i + self.codebase_chunksize])

    # Model Loading / saving
    def save_model_epoch(self, model, epoch):
        if not os.path.exists(self.path + 'models/' + self.model_params['model_name'] + '/'):
            os.makedirs(self.path + 'models/' + self.model_params['model_name'] + '/')
        model.save(self.path + 'models/' + self.model_params['model_name'] + '/epo%d_code.h5' % epoch,
                   self.path + 'models/' + self.model_params['model_name'] + '/epo%d_desc.h5' % epoch, overwrite=True)

    def load_model_epoch(self, model, epoch):
        assert os.path.exists(
            self.path + 'models/' + self.model_params[
                'model_name'] + '/epo%d_code.h5' % epoch), 'Weights at epoch %d not found' % epoch
        assert os.path.exists(
            self.path + 'models/' + self.model_params[
                'model_name'] + '/epo%d_desc.h5' % epoch), 'Weights at epoch %d not found' % epoch
        model.load(self.path + 'models/' + self.model_params['model_name'] + '/epo%d_code.h5' % epoch,
                   self.path + 'models/' + self.model_params['model_name'] + '/epo%d_desc.h5' % epoch)

    # Training
    def train(self, model):
        log_every = self.model_params['log_every']
        valid_every = self.model_params['valid_every']
        save_every = self.model_params['save_every']
        batch_size = self.model_params['batch_size']
        nb_epoch = self.model_params['nb_epoch']

        train_set = CodeSearchDataset(self.path,
                                      self.model_params['train_name'], self.model_params['name_len'],
                                      self.model_params['train_api'], self.model_params['api_len'],
                                      self.model_params['train_tokens'], self.model_params['tokens_len'],
                                      self.model_params['train_desc'], self.model_params['desc_len'])

        data_loader = torch.utils.data.DataLoader(dataset=train_set, batch_size=self.model_params['batch_size'],
                                                  shuffle=True, drop_last=True, num_workers=1)

        for epoch in range(self.model_params['reload'] + 1, nb_epoch):
            itr = 1
            losses = []
            for names, apis, toks, good_descs, bad_descs in data_loader:
                names, apis, toks, good_descs, bad_descs = gVar(names), gVar(apis), gVar(toks), gVar(good_descs), gVar(
                    bad_descs)
                loss = model(names, apis, toks, good_descs, bad_descs)
                losses.append(loss.item())
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                if itr % log_every == 0:
                    logger.info(f'epo:[{epoch:d}/{nb_epoch:d}] itr:{itr:d} Loss={np.mean(losses):.5f}')
                    losses = []
                itr = itr + 1

            if epoch and epoch % valid_every == 0:
                self.eval(model, 1000, 1)

            if epoch and epoch % save_every == 0:
                self.save_model_epoch(model, epoch)

    # Evaluation
    def eval(self, model, poolsize, K):
        """
        simple validation in a code pool. 
        @param: poolsize - size of the code pool, if -1, load the whole test set
        """

        def ACC(real, predict):
            _sum = 0.0
            for val in real:
                try:
                    index = predict.index(val)
                except ValueError:
                    index = -1
                if index != -1:
                    _sum = _sum + 1
            return _sum / float(len(real))

        def MAP(real, predict):
            _sum = 0.0
            for _id, val in enumerate(real):
                try:
                    index = predict.index(val)
                except ValueError:
                    index = -1
                if index != -1:
                    _sum = _sum + (_id + 1) / float(index + 1)
            return _sum / float(len(real))

        def MRR(real, predict):
            _sum = 0.0
            for val in real:
                try:
                    index = predict.index(val)
                except ValueError:
                    index = -1
                if index != -1:
                    _sum = _sum + 1.0 / float(index + 1)
            return _sum / float(len(real))

        def NDCG(real, predict):
            dcg = 0.0
            idcg = IDCG(len(real))
            for i, predictItem in enumerate(predict):
                if predictItem in real:
                    itemRelevance = 1
                    rank = i + 1
                    dcg += (math.pow(2, itemRelevance) - 1.0) * (math.log(2) / math.log(rank + 1))
            return dcg / float(idcg)

        def IDCG(n):
            idcg = 0
            itemRelevance = 1
            for i in range(n):
                idcg += (math.pow(2, itemRelevance) - 1.0) * (math.log(2) / math.log(i + 2))
            return idcg

        # load test dataset
        valid_set = CodeSearchDataset(self.path,
                                      self.model_params['valid_name'], self.model_params['name_len'],
                                      self.model_params['valid_api'], self.model_params['api_len'],
                                      self.model_params['valid_tokens'], self.model_params['tokens_len'],
                                      self.model_params['valid_desc'], self.model_params['desc_len'])

        data_loader = torch.utils.data.DataLoader(dataset=valid_set, batch_size=poolsize,
                                                  shuffle=True, drop_last=True, num_workers=1)

        acc, mrr, map, ndcg = 0, 0, 0, 0
        n_pools = 0
        for names, apis, toks, descs, _ in data_loader:
            n_pools += 1
            names, apis, toks = gVar(names), gVar(apis), gVar(toks)
            code_repr = model.code_encoding(names, apis, toks)
            for i in range(poolsize):
                desc = gVar(descs[i].expand(poolsize, -1))
                desc_repr = model.desc_encoding(desc)
                n_results = K
                sims = F.cosine_similarity(code_repr, desc_repr).data.cpu().numpy()
                negsims = np.negative(sims)
                predict = np.argsort(negsims)  # predict = np.argpartition(negsims, kth=n_results-1)
                predict = predict[:n_results]
                predict = [int(k) for k in predict]
                real = [i]
                acc += ACC(real, predict)
                mrr += MRR(real, predict)
                map += MAP(real, predict)
                ndcg += NDCG(real, predict)
        acc = acc / n_pools / poolsize
        mrr = mrr / n_pools / poolsize
        map = map / n_pools / poolsize
        ndcg = ndcg / n_pools / poolsize
        logger.info('ACC={}, MRR={}, MAP={}, nDCG={}'.format(acc, mrr, map, ndcg))

        return acc, mrr, map, ndcg

    #Compute Representation
    def repr_code(self, model):
        vecs = None
        use_set = CodeSearchDataset(self.model_params['workdir'],
                                    self.model_params['use_names'], self.model_params['name_len'],
                                    self.model_params['use_apis'], self.model_params['api_len'],
                                    self.model_params['use_tokens'], self.model_params['tokens_len'])

        data_loader = torch.utils.data.DataLoader(dataset=use_set, batch_size=1000,
                                                  shuffle=False, drop_last=False, num_workers=1)
        for names, apis, toks in data_loader:
            names, apis, toks = gVar(names), gVar(apis), gVar(toks)
            reprs = model.code_encoding(names, apis, toks).data.cpu().numpy()
            vecs = reprs if vecs is None else np.concatenate((vecs, reprs), 0)
        vecs = normalize(vecs)
        save_vecs(vecs, self.path + self.model_params['use_codevecs'])
        return vecs

    def search(self, model, query, n_results=10):
        desc = sent2indexes(query, self.vocab_desc)  # convert desc sentence into word indices
        desc = np.expand_dims(desc, axis=0)
        desc = gVar(desc)
        desc_repr = model.desc_encoding(desc).data.cpu().numpy()

        codes = []
        sims = []
        threads = []
        for i, codevecs_chunk in enumerate(self.codevecs):
            t = threading.Thread(target=self.search_thread, args=(codes, sims, desc_repr, codevecs_chunk, i, n_results))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:  # wait until all sub-threads finish
            t.join()
        return codes, sims

    def search_thread(self, codes, sims, desc_repr, codevecs, i, n_results):
        # 1. compute code similarities
        chunk_sims = dot_np(normalize(desc_repr), codevecs)

        # 2. choose the top K results
        negsims = np.negative(chunk_sims[0])
        maxinds = np.argpartition(negsims, kth=n_results - 1)
        maxinds = maxinds[:n_results]
        chunk_codes = [self.codebase[i][k] for k in maxinds]
        chunk_sims = chunk_sims[0][maxinds]
        codes.extend(chunk_codes)
        sims.extend(chunk_sims)


def parse_args():
    parser = argparse.ArgumentParser("Train and Test Code Search(Embedding) Model")
    parser.add_argument("--mode", choices=["train", "eval", "repr_code", "search"], default='train',
                        help="The mode to run. The `train` mode trains a model;"
                             " the `eval` mode evaluat models in a test set "
                             " The `repr_code/repr_desc` mode computes vectors"
                             " for a code snippet or a natural language description with a trained model.")
    parser.add_argument("--verbose", action="store_true", default=True, help="Be verbose")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    conf = get_config()
    searcher = CodeSearcher(conf)

    #Define model
    logger.info('Build Model')
    if conf['reload'] > 0:
        _model = searcher.load_model_epoch(conf['reload'])
    else:
        _model = JointEmbeder(conf)  # initialize the model
    _model = _model.cuda() if torch.cuda.is_available() else _model

    optimizer = optim.Adam(_model.parameters(), lr=conf['lr'])

    if args.mode == 'train':
        searcher.train(_model)

    elif args.mode == 'eval':
        # evaluate for a particular epoch
        searcher.eval(_model, 1000, 10)

    elif args.mode == 'repr_code':
        vecs = searcher.repr_code(_model)

    elif args.mode == 'search':
        # search code based on a desc
        searcher.load_codevecs()
        searcher.load_codebase()
        while True:
            try:
                query = input('Input Query: ')
                n_results = int(input('How many results? '))
            except Exception:
                print("Exception while parsing your input:")
                traceback.print_exc()
                break
            codes, sims = searcher.search(_model, query, n_results)
            zipped = zip(codes, sims)
            results = '\n\n'.join(map(str, zipped))  # combine the result into a returning string
            print(results)
