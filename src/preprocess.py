import csv
import pickle
import re
import subprocess
from ast import literal_eval
from collections import defaultdict

import lmdb
import pandas as pd

csv.field_size_limit(922337203)
total = 31703079  # 33369383
comments = 6739641
split = 0.2

train_size = comments * (1 - split)
valid_size = comments * split

path = "./data/java_corpus/"
train_file_name = "java_train.csv"

main_file = path + "method_db_cleaned.csv"
clean_file = path + "method_db_clean.csv"
comment_file = path + "java_comment.csv"
train_file = path + train_file_name
valid_file = path + "java_valid.csv"
use_file = path + "java_use.csv"
use_code_file = path + "use.rawcode.txt"

name_vocab = path + "nameVocab.csv"
api_vocab = path + "apiVocab.csv"
token_vocab = path + "tokenVocab.csv"
desc_vocab = path + "commentVocab.csv"

name_vocab_pkl = path + "vocab.methname.pkl"
api_vocab_pkl = path + "vocab.apiseq.pkl"
token_vocab_pkl = path + "vocab.tokens.pkl"
desc_vocab_pkl = path + "vocab.desc.pkl"


def split_comment(comment):
    return re.findall(r"[\w]+", comment.lower())


def parse_method(method):
    return literal_eval(
        subprocess.check_output(["java", "-jar", "JavaParser.jar", "{}".format(method)]).decode('utf-8').strip())


def training_generator():
    with open(comment_file, 'r', encoding='utf8') as f:
        with open(train_file, 'w', encoding='utf8', newline='') as train, open(valid_file, 'w', encoding='utf8',
                                                                               newline='') as valid:
            reader = csv.reader(f)
            train_writer = csv.writer(train)
            valid_writer = csv.writer(valid)
            for i, line in enumerate(reader):
                train_writer.writerow(line) if i < train_size else valid_writer.writerow(line)


def filter_comment():
    with open(clean_file, 'r', encoding='utf8') as f:
        with open(comment_file, 'w', encoding='utf8', newline='') as comment:
            with open(use_code_file, 'w', encoding='utf8', newline='') as use_code, open(use_file, 'w',
                                                                                         encoding='utf8',
                                                                                         newline='') as use:
                reader = csv.reader(f)
                comment_writer = csv.writer(comment)
                use_writer = csv.writer(use)
                use_code_writer = csv.writer(use_code)
                for line in reader:
                    _comment = split_comment(line[1])
                    container = parse_method(line[2])
                    _name, _api, _token = container["name"], container["api"], container["token"]

                    if line[1] != "":
                        comment_writer.writerow([_name, _api, _token, _comment])

                    use_writer.writerow([_name, _api, _token, []])
                    use_code_writer.writerow([line[2]])


def clean_nulls():
    with open(main_file, 'r', encoding='utf8') as _in, open(clean_file, 'w', encoding='utf8', newline='') as _out:
        next(_in)
        for line in _in:
            _out.write(line.replace('\0', ''))


def generate_vocab():
    _name_vocab = defaultdict(int)
    _api_vocab = defaultdict(int)
    _token_vocab = defaultdict(int)
    _comment_vocab = defaultdict(int)
    with open(train_file, 'r', encoding='utf8') as train:
        train_reader = csv.reader(train)
        for _name, _api, _token, _comment in train_reader:

            for name_token in literal_eval(_name):
                if not (name_token == "" or name_token != " " or name_token != "_"):
                    _name_vocab[name_token] += 1

            for api_token in literal_eval(_api):
                if not (api_token == "" or api_token != " " or api_token != "_"):
                    _api_vocab[api_token] += 1

            for body_token in literal_eval(_token):
                if not (body_token == "" or body_token != " " or body_token != "_"):
                    _token_vocab[body_token] += 1

            for comment_token in literal_eval(_comment):
                if not (comment_token == "" or comment_token != " " or comment_token != "_"):
                    _comment_vocab[comment_token] += 1

    with open(name_vocab, 'w', encoding='utf8', newline='') as vocab:
        vocab_writer = csv.writer(vocab)
        vocab_writer.writerow(["word", "id", "occ"])
        for i, (t, count) in enumerate(sorted(list(_name_vocab.items()), key=lambda x: x[1], reverse=True), start=2):
            vocab_writer.writerow([t, i, count])

    with open(api_vocab, 'w', encoding='utf8', newline='') as vocab:
        vocab_writer = csv.writer(vocab)
        vocab_writer.writerow(["word", "id", "occ"])
        for i, (t, count) in enumerate(sorted(list(_api_vocab.items()), key=lambda x: x[1], reverse=True), start=2):
            vocab_writer.writerow([t, i, count])

    with open(token_vocab, 'w', encoding='utf8', newline='') as vocab:
        vocab_writer = csv.writer(vocab)
        vocab_writer.writerow(["word", "id", "occ"])
        for i, (t, count) in enumerate(sorted(list(_token_vocab.items()), key=lambda x: x[1], reverse=True), start=2):
            vocab_writer.writerow([t, i, count])

    with open(desc_vocab, 'w', encoding='utf8', newline='') as vocab:
        vocab_writer = csv.writer(vocab)
        vocab_writer.writerow(["word", "id", "occ"])
        for i, (t, count) in enumerate(sorted(list(_comment_vocab.items()), key=lambda x: x[1], reverse=True), start=2):
            vocab_writer.writerow([t, i, count])


def generate_pickle_vocab():
    df = pd.read_csv(name_vocab)
    with open(name_vocab_pkl, 'wb') as f:
        pickle.dump(df[["word", "id"]], f)

    df = pd.read_csv(api_vocab)
    with open(api_vocab_pkl, 'wb') as f:
        pickle.dump(df[["word", "id"]], f)

    df = pd.read_csv(token_vocab)
    with open(token_vocab_pkl, 'wb') as f:
        pickle.dump(df[["word", "id"]], f)

    df = pd.read_csv(desc_vocab)
    with open(desc_vocab_pkl, 'wb') as f:
        pickle.dump(df[["word", "id"]], f)


def load_in_db(name, file, map_size=1e10):
    env = lmdb.open(name, map_size=map_size)

    with open(file, 'r', encoding='utf8') as f:
        reader = csv.reader(f)
        with env.begin(write=True) as txn:
            for i, (_name, _api, _token, _comment) in enumerate(reader):
                row_id = '{:09}'.format(i)
                data = (literal_eval(_name), literal_eval(_api), literal_eval(_token), literal_eval(_comment))
                txn.put(row_id.encode('ascii'), pickle.dumps(data))


if __name__ == "__main__":
    # print("Cleaning null bytes")
    # clean_nulls()
    print("Separating comments and raw code")
    filter_comment()
    print("Splitting train and validation datasets")
    training_generator()
    print("Generating vocabulary")
    generate_vocab()
    print("Pickling vocabulary")
    generate_pickle_vocab()
    print("Loading train dataset in database")
    load_in_db("java_train", train_file, map_size=3e9)
    print("Loading validation dataset in database")
    load_in_db("java_valid", valid_file, map_size=1e9)
    print("Loading use dataset in database")
    load_in_db("java_use", use_file, map_size=1.5e10)
