import argparse
import logging
import math
import os
import random
import threading

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
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s", filename="logger.debug.log")

console = logging.StreamHandler()
console.setLevel(logging.INFO)

formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


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
        self.codebase_chunksize = conf['chunk_size']

    # Data Set
    def load_codebase(self):
        """load codebase
        codefile: file that stores raw code
        """
        logger.info('Loading codebase (chunk size={})'.format(self.codebase_chunksize))
        if not self.codebase:  # empty
            # TODO: there are some weird encoding issues so just ignore them for now
            with open(self.path + self.model_params['use_codebase'], errors='ignore') as f:
                codes = f.readlines()
                logging.debug("Loading codebase: {} groups".format(len(codes) // self.codebase_chunksize))
                for i in range(0, len(codes), self.codebase_chunksize):
                    logging.debug("loading [{}/{}]".format(i // self.codebase_chunksize, len(codes) // self.codebase_chunksize))
                    self.codebase.append(codes[i:i + self.codebase_chunksize])

    # Results Data
    def load_codevecs(self):
        """read vectors (2D numpy array) from a hdf5 file"""
        logger.debug('Loading code vectors..')
        if not self.codevecs:  # empty
            reprs = load_vecs(self.path + self.model_params['use_codevecs'])
            logging.debug("Loading codevecs: {} groups".format(len(reprs) // self.codebase_chunksize))
            for i in range(0, reprs.shape[0], self.codebase_chunksize):
                logging.debug("loading [{}/{}]".format(i, len(reprs) // self.codebase_chunksize))
                self.codevecs.append(reprs[i:i + self.codebase_chunksize])

    # Model Loading / saving
    def save_model_epoch(self, model, epoch):
        if not os.path.exists('{}models/{}/'.format(self.path, self.model_params['model_name'])):
            os.makedirs('{}models/{}/'.format(self.path, self.model_params['model_name']))
        torch.save(model.state_dict(),
                   '{}models/{}/epo{}_code.h5'.format(self.path, self.model_params['model_name'], epoch))

    def load_model_epoch(self, model, epoch):
        assert os.path.exists('{}models/{}/epo{}_code.h5'.format(self.path, self.model_params['model_name'],
                                                                 epoch)), 'Weights at epoch {} not found'.format(epoch)
        model.load_state_dict(
            torch.load('{}models/{}/epo{}_code.h5'.format(self.path, self.model_params['model_name'], epoch)))

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
                                      self.model_params['train_desc'], self.model_params['desc_len'],
                                      load_in_memory=True)

        data_loader = torch.utils.data.DataLoader(dataset=train_set, batch_size=batch_size,
                                                  shuffle=True, drop_last=True, num_workers=4, pin_memory=True)

        # TODO: generate an epoch loss to monitor training
        for epoch in range(self.model_params['reload'] + 1, nb_epoch):
            losses = []
            for itr, (names, apis, toks, good_descs, bad_descs) in enumerate(data_loader, start=1):
                names, apis, toks, good_descs, bad_descs = gVar(names), gVar(apis), gVar(toks), gVar(good_descs), gVar(
                    bad_descs)
                loss = model.train()(names, apis, toks, good_descs, bad_descs)
                losses.append(loss.item())
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                if itr % log_every == 0:
                    logger.info('epo:[{}/{}] itr:{} Loss={:.5f}'.format(epoch, nb_epoch, itr, np.mean(losses)))
                    losses = []

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
                                      self.model_params['valid_desc'], self.model_params['desc_len'],
                                      load_in_memory=True)

        data_loader = torch.utils.data.DataLoader(dataset=valid_set, batch_size=poolsize,
                                                  shuffle=True, drop_last=True, num_workers=1, pin_memory=True)

        _acc, _mrr, _map, _ndcg = 0, 0, 0, 0
        n_pools = 0
        for names, apis, toks, descs, _ in data_loader:
            n_pools += 1
            names, apis, toks = gVar(names), gVar(apis), gVar(toks)
            code_repr = model.eval().code_encoding(names, apis, toks)
            for it in range(poolsize):
                desc = gVar(descs[it].expand(poolsize, -1))
                desc_repr = model.eval().desc_encoding(desc)
                n_results = K
                sims = F.cosine_similarity(code_repr, desc_repr).data.cpu().numpy()
                negsims = np.negative(sims)
                prediction = np.argsort(negsims)  # predict = np.argpartition(negsims, kth=n_results-1)
                prediction = prediction[:n_results]
                prediction = [int(k) for k in prediction]
                real_value = [it]
                _acc += ACC(real_value, prediction)
                _mrr += MRR(real_value, prediction)
                _map += MAP(real_value, prediction)
                _ndcg += NDCG(real_value, prediction)
        _acc = _acc / n_pools / poolsize
        _mrr = _mrr / n_pools / poolsize
        _map = _map / n_pools / poolsize
        _ndcg = _ndcg / n_pools / poolsize
        logger.info('ACC={}, MRR={}, MAP={}, nDCG={}'.format(_acc, _mrr, _map, _ndcg))

        return _acc, _mrr, _map, _ndcg

    # Compute Representation
    def repr_code(self, model, norm=True):
        logging.info("Start Code Representation")
        use_set = CodeSearchDataset(self.model_params['workdir'],
                                    self.model_params['use_names'], self.model_params['name_len'],
                                    self.model_params['use_apis'], self.model_params['api_len'],
                                    self.model_params['use_tokens'], self.model_params['tokens_len'],
                                    load_in_memory=True)

        data_loader = torch.utils.data.DataLoader(dataset=use_set, batch_size=1000,
                                                  shuffle=False, drop_last=False, num_workers=2, pin_memory=True)

        vecs = []
        logging.debug("Calculating code vectors")
        for itr, (names, apis, toks) in enumerate(data_loader, start=1):
            names, apis, toks = gVar(names), gVar(apis), gVar(toks)
            reprs = model.eval().code_encoding(names, apis, toks).data.cpu().numpy()
            vecs.append(reprs)
            if itr % 100 == 0:
                logger.info('itr:{}/{}'.format(itr, len(use_set) // 1000))

        logging.debug("Concatenating all vectors")
        vecs = np.concatenate(vecs, 0)

        if norm:
            logger.debug("Normalizing...")
            vecs = normalize(vecs)

        logging.debug("Writing to disk -  vectors")
        save_vecs(vecs, self.path + self.model_params['use_codevecs'])
        return vecs

    def search(self, model, query, n_results=10):
        desc = sent2indexes(query, self.vocab_desc)  # convert desc sentence into word indices
        logger.debug("Description representation")
        logger.debug(desc)
        desc = np.expand_dims(desc, axis=0)
        desc = gVar(desc)
        logger.debug("Description embedding")
        desc_repr = model.eval().desc_encoding(desc).data.cpu().numpy()
        logger.debug(desc_repr)

        valued = []
        threads = []
        for i, codevecs_chunk in enumerate(self.codevecs):
            # select the best n_results from each chunk
            t = threading.Thread(target=self.search_thread,
                                 args=(valued, desc_repr, codevecs_chunk, i, n_results))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:  # wait until all sub-threads finish
            t.join()

        valued.sort(reverse=True)

        logger.debug(valued)

        return valued[:n_results]

    def search_thread(self, valued, desc_repr, codevecs, i, n_results):
        # 1. compute code similarities
        chunk_sims = dot_np(normalize(desc_repr), codevecs)

        # 2. choose the top K results
        negsims = np.negative(chunk_sims[0])
        maxinds = np.argpartition(negsims, kth=n_results - 1)
        maxinds = maxinds[:n_results]
        logger.debug("max inds")
        logger.debug(maxinds)
        valued.extend((chunk_sims[0][k], self.codebase[i][k]) for k in maxinds)


def parse_args():
    parser = argparse.ArgumentParser("Train and Test Code Search(Embedding) Model")
    parser.add_argument("--mode", choices=["train", "eval", "repr_code", "search"], default='train',
                        help="The mode to run. The `train` mode trains a model;"
                             " the `eval` mode evaluate models in a test set "
                             " The `repr_code/repr_desc` mode computes vectors"
                             " for a code snippet or a natural language description with a trained model.")
    parser.add_argument("--verbose", action="store_true", default=True, help="Be verbose")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    conf = get_config()
    searcher = CodeSearcher(conf)

    # Define model
    logger.info('Build Model')
    _model = JointEmbeder(conf)  # initialize the model

    if conf['reload'] > 0:
        searcher.load_model_epoch(_model, conf['reload'])

    _model = _model.cuda() if torch.cuda.is_available() else _model

    optimizer = optim.Adam(_model.parameters(), lr=conf['lr'])

    if args.mode == 'train':
        logging.info("Start Training")
        searcher.train(_model)

    elif args.mode == 'eval':
        logging.info("Start eval")
        # evaluate for a particular epoch
        searcher.eval(_model, 1000, 10)

    elif args.mode == 'repr_code':
        logging.info("Start code representation")
        searcher.repr_code(_model)

    elif args.mode == 'search':
        logging.info("Start Searching")
        # search code based on a desc
        searcher.load_codevecs()
        searcher.load_codebase()
        while True:
            try:
                print("-" * 20)
                _query = input('Input Query: ')
                number_results = int(input('How many results? '))
            except Exception as e:
                print("Exception while parsing your input:")
                print(e)
                break
            snippets = searcher.search(_model, _query, number_results)
            results = '\n\n'.join(map(str, snippets))  # combine the result into a returning string
            print(results)
            print("-" * 20)
