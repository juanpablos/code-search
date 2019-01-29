import csv
import pickle

import jnius_config
import lmdb
import pandas as pd

jnius_config.set_classpath('./*')
from jnius import autoclass

csv.field_size_limit(922337203)
total = 33369383
comments = 7146092
split = 0.2

train_size = comments * (1 - split)
valid_size = comments * split

path = "data/java_corpus/"

main_file = path + "method_db.csv"
clean_file = path + "method_db_clean.csv"
comment_file = path + "java_comment.csv"
train_file = path + "java_train.csv"
valid_file = path + "java_valid.csv"
use_file = path + "java_use.csv"
use_code_file = path + "use.rawcode.txt"

name_vocab = path + "nameVocab.csv"
api_vocab = path + "apiVocab.csv"
token_vocab = path + "tokenVocab.csv"
desc_vocab = path + "commentVocab.csv"


def training_generator():
    with open(comment_file, 'r', encoding='utf8') as f:
        with open(train_file, 'w', encoding='utf8', newline='') as train, open(valid_file, 'w', encoding='utf8',
                                                                               newline='') as valid:
            reader = csv.reader(f)
            train_writer = csv.writer(train)
            valid_writer = csv.writer(valid)
            lines = 0
            for line in reader:
                if lines < train_size:
                    train_writer.writerow([line[1], line[2]])
                else:
                    valid_writer.writerow([line[1], line[2]])

                lines += 1


def filter_comment():
    with open(clean_file, 'r', encoding='utf8') as f:
        with open(comment_file, 'w', encoding='utf8', newline='') as comment:
            with open(use_code_file, 'w', encoding='utf8', newline='') as use_code, open(use_code_file, 'w',
                                                                                         encoding='utf8',
                                                                                         newline='') as use:
                reader = csv.reader(f)
                comment_writer = csv.writer(comment)
                use_writer = csv.writer(use)
                use_code_writer = csv.writer(use_code)
                for line in reader:
                    if line[1] != "":
                        comment_writer.writerow(line)

                    use_code_writer.writerow([line[2]])
                    use_writer.writerow([line[1], line[2]])


def clean_nulls():
    with open(main_file, 'r', encoding='utf8') as _in, open(clean_file, 'w', encoding='utf8', newline='') as _out:
        next(_in)
        for line in _in:
            _out.write(line.replace('\0', ''))


def generate_vocab():
    generator = autoclass('parser.Vocabulary')()
    generator.generateVocabulary(clean_file)


def generate_pickle_vocab():
    df = pd.read_csv(name_vocab)
    with open("./data/java_corpus/vocab.methname.pkl", 'wb') as f:
        pickle.dump(df[["word", "id"]], f)

    df = pd.read_csv(api_vocab)
    with open("./data/java_corpus/vocab.apiseq.pkl", 'wb') as f:
        pickle.dump(df[["word", "id"]], f)

    df = pd.read_csv(token_vocab)
    with open("./data/java_corpus/vocab.tokens.pkl", 'wb') as f:
        pickle.dump(df[["word", "id"]], f)

    df = pd.read_csv(desc_vocab)
    with open("./data/java_corpus/vocab.desc.pkl", 'wb') as f:
        pickle.dump(df[["word", "id"]], f)


def load_in_db(name, file, map_size=1e10):
    env = lmdb.open(name, map_size=map_size)

    with open(file, 'r', encoding='utf8') as f:
        reader = csv.reader(f)
        with env.begin(write=True) as txn:
            for i, line in enumerate(reader):
                row_id = '{:09}'.format(i)
                data = (line[0], line[1])
                txn.put(row_id.encode('ascii'), pickle.dumps(data))


if __name__ == "__main__":
    clean_nulls()
    filter_comment()
    training_generator()
    generate_vocab()
    generate_pickle_vocab()

    load_in_db("java_train", train_file)
    load_in_db("java_valid", valid_file, map_size=5e9)
    load_in_db("java_use", use_file, map_size=1.5e10)
