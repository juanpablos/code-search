import csv
import logging
import os
import shutil
import subprocess
import sys
from itertools import repeat

# TODO: right now we select only the biggest SIVA file, this might be inaccurate
# Best way would be to unpack every siva file for a repository, then compare their references and timestamps

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(asctime)s %(message)s", filename="logger.log")

console = logging.StreamHandler()
console.setLevel(logging.INFO)

errors = logging.FileHandler("errors.log")
errors.setLevel(logging.WARNING)

formatter = logging.Formatter('%(levelname)s %(message)s')

console.setFormatter(formatter)
errors.setFormatter(formatter)
logger.addHandler(console)
logger.addHandler(errors)


def no_heads(references):
    return [i.split(" ")[-1] for i in references.split("\n")]


siva_path = "./siva/latest"
repos_path = "./repos"
index_file_path = "./index.csv"

logger.debug("Making repo dir")
os.makedirs(repos_path, exist_ok=True)

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


with open(index_file_path) as f:
    index = csv.reader(f)

    for row in index:
        author = row[0].split('/')[-2]
        name = row[0].split('/')[-1]
        logger.info("Unpacking {} {}".format(author, name))

        siva_files = row[1].split(",")
        comp = dict(zip(siva_files, repeat(0, len(siva_files))))
        one = False
        for file in siva_files:
            try:
                comp[file] = os.path.getsize("{path}/{hash}/{file}".format(path=siva_path, hash=file[:2], file=file))
                one = True
            except FileNotFoundError:
                logger.debug("{} not found".format(file))
                pass

        if not one:
            # no siva file found
            logger.warning("No siva file found for {} {}".format(author, name))
            logger.debug("Skipping")
            continue

        biggest_siva = max(comp.items(), key=lambda x: x[1])[0]
        biggest_path = "{path}/{hash}/{file}".format(path=siva_path, hash=biggest_siva[:2], file=biggest_siva)

        repo_dir = "{repo_path}/{author}/{name}/.git/".format(repo_path=repos_path, author=author, name=name)

        logger.debug("Extracting {} to {}".format(biggest_siva, repo_dir))
        os.makedirs(repo_dir)

        logger.info("Extracting {}".format(biggest_siva))
        subprocess.run(["siva", "unpack", biggest_path, repo_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        wd = os.getcwd()
        # .git/ must be removed
        logger.debug("Changing dir to {}".format(repo_dir[:-5]))
        os.chdir(repo_dir[:-5])
        # choose a head ref to checkout
        logger.debug("Calling show ref...")
        try:
            newest_ref = subprocess.check_output(
                ["git", "for-each-ref", "refs/heads", "--sort=-authordate", "--count=1", "--format='%(refname)'"])
            newest_ref = newest_ref.strip(b"\n'")

            if not newest_ref:
                logger.debug("No HEAD matches")
                logger.debug("Falling back to any ref")
                newest_ref = subprocess.check_output(
                    ["git", "for-each-ref", "--sort=-authordate", "--count=1", "--format='%(refname)'"])
                newest_ref = newest_ref.strip(b"\n'")

        except Exception as e:
            logger.critical("Error with the reference handling")
            logger.critical("{}".format(e))
            logger.critical("{} {} {}".format(author, name, biggest_siva))
        else:
            try:
                logger.debug("Newest head reference {}".format(newest_ref.decode('utf-8')))
                # git checkout ref
                logger.info("Checking out reference")
                subprocess.run(["git", "checkout", newest_ref.decode('utf-8')], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except:
                logger.critical("Error handling reference for {} {}".format(author, name))
                logger.critical("Reference is {}".format(newest_ref.decode('ascii', errors='ignore')))
                pass

        finally:
            logger.debug("Changing dir to {}".format(wd))
            os.chdir(wd)
            logger.debug("Cleaning .git directory")
            shutil.rmtree(repo_dir, ignore_errors=True)
