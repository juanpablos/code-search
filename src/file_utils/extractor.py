import csv
import hashlib
import logging
import os
import shutil

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(asctime)s %(message)s", filename="ext_logger.log")

console = logging.StreamHandler()
console.setLevel(logging.INFO)

errors = logging.FileHandler("ext_errors.log")
errors.setLevel(logging.WARNING)

formatter = logging.Formatter('%(levelname)s %(message)s')

console.setFormatter(formatter)
errors.setFormatter(formatter)
logger.addHandler(console)

# File definitions
index_file = os.path.abspath("./index.csv")
repos_path = os.path.abspath("./repos")
files_path = os.path.abspath("./corpus")

search_for = ['java', 'python']

db_file = files_path + "/db.csv"
java_path = files_path + "/java"
python_path = files_path + "/python"

logger.debug("Making java dir")
os.makedirs(java_path, exist_ok=True)
logger.debug("Making python dir")
os.makedirs(python_path, exist_ok=True)

# 64kb
BUF_SIZE = 65536
logger.debug("Reading with {} bytes".format(BUF_SIZE // 1024))


def hash_file(filename):
    with open(filename, 'rb') as source_file:
        logger.debug("Hashing {}".format(filename))
        sha1 = hashlib.sha1()
        while True:
            data = source_file.read(BUF_SIZE)
            if not data:
                logger.debug("Completed hash for {}".format(filename))
                return sha1.hexdigest()
            sha1.update(data)
            logger.debug("Updated hash for {}".format(filename))


fieldnames = ["author", "repository", "path", "name", "language", "hash"]
logger.info("Creating db file")
with open(db_file, 'x', newline='') as o:
    writer = csv.DictWriter(o, fieldnames=fieldnames)
    writer.writeheader()

with open(index_file, encoding="utf-8") as f:
    reader = csv.reader(f)

    for line in reader:
        url = line[0].split('/')
        author = url[-2]
        repo = url[-1]
        logger.info("Checking {} - {}".format(author, repo))

        langs = line[3].lower().split(',')

        if not any(l in langs for l in search_for):
            logger.warning("Sought language is not present")
            logger.debug("Skipping")
            continue

        logger.info("Language found")
        wd = os.getcwd()
        # change dir to author/repo
        to_search = "{}/{}/{}".format(repos_path, author, repo)
        logger.debug("Changing dir to {}".format(to_search))
        os.chdir(to_search)
        with open(db_file, 'a', newline='') as o:
            writer = csv.DictWriter(o, fieldnames=fieldnames)

            # list all files and search for extensions
            for root, dirnames, filenames in os.walk('.'):
                logger.debug("Searching in {}".format(root))
                for file in filenames:
                    line = {}

                    # TODO: refactor
                    if file.lower().endswith('.java'):
                        line['language'] = 'java'
                    elif file.lower().endswith('.py'):
                        line['language'] = 'python'
                    else:
                        logger.debug("{} is not in the language list".format(file))
                        continue

                    line['author'] = author
                    line['repository'] = repo
                    line['name'] = file
                    # remove the dot (.)
                    line['path'] = root[1:]

                    file_hash = hash_file(os.path.join(root, file))
                    line['hash'] = file_hash

                    # write in index | java | python
                    logger.info("Writing file {}".format(file))
                    writer.writerow(line)

                    # copy | java dir | python dir
                    logger.info("Copying file {}".format(file))
                    shutil.copyfile(os.path.join(root, file),
                                    "{}/{}/{}".format(files_path, line['language'], file_hash))

        # change dir to root
        logger.debug("Changing dir to {}".format(wd))
        os.chdir(wd)
        logger.debug("Force writing")
        f.flush()
        os.fsync(f.fileno())