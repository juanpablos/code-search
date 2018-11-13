import csv
import hashlib
import logging
import os
import shutil
import sys

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

######### NEVER DO THIS AGAIN #########
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt / 10)
    else:
        break


##################


def hash_file(filename):
    try:
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
    except FileNotFoundError as ex:
        logger.critical("{}".format(ex))
        logger.critical("Cant open file {}".format(filename))
        raise


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
        logger.info("Checking {}/{}".format(author, repo))

        langs = line[3].lower().split(',')

        if not any(l in langs for l in search_for):
            logger.warning("Sought language is not present")
            logger.debug("Skipping")
            continue

        logger.info("Language found")
        wd = os.getcwd()
        # change dir to author/repo
        to_search = "{}/{}/{}".format(repos_path, author, repo)
        try:
            logger.debug("Changing dir to {}".format(to_search))
            os.chdir(to_search)
        except FileNotFoundError:
            logger.warning("Path cannot be found")
            logger.debug("{} is an unpacked repository".format(to_search))
        else:
            with open(db_file, 'a', newline='') as o:
                writer = csv.DictWriter(o, fieldnames=fieldnames)

                # list all files and search for extensions
                for root, dirnames, filenames in os.walk('.'):
                    logger.debug("Searching in {}".format(root))
                    for file in filenames:
                        try:
                            logger.debug("Looking at file {}".format(file))
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
                            line['path'] = root[2:]

                            try:
                                file_hash = hash_file(os.path.join(root, file))
                            except Exception:
                                logger.critical("Problem while hashing {}/{}".format(root, file))
                                logger.warning("Skipping file")
                                continue

                            line['hash'] = file_hash

                            # copy | java dir | python dir
                            logger.info("Copying file {}".format(file))
                            try:
                                shutil.copyfile(os.path.join(root, file),
                                                "{}/{}/{}".format(files_path, line['language'], file_hash))
                            except IOError as e:
                                logger.critical("{}".format(e))
                                logger.critical("Problem while copying {}/{}".format(root, file))
                            else:
                                # write in index | java | python
                                # only write if no problem occurs
                                logger.info("Writing file {} to db".format(file))
                                writer.writerow(line)
                        except Exception as e:
                            logger.critical("{}".format(e))
                            logger.critical("Error while working with repo {}/{}".format(author, repo))
                            logger.critical("Unrecoverable error with file {}/{}".format(
                                root.encode("utf8", errors="surrogateescape").decode("utf8", errors="surrogateescape"),
                                file.encode("utf8", errors="surrogateescape").decode("utf8", errors="surrogateescape")))
                            continue

        finally:
            # change dir to root
            logger.debug("Changing dir to {}".format(wd))
            os.chdir(wd)
            logger.debug("Force writing")
            f.flush()
            os.fsync(f.fileno())
