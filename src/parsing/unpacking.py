import csv
import logging
import os
import re
import shutil
import subprocess
import sys
from itertools import repeat

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


siva_path = "../../../../Go/siva/latest"
repos_path = siva_path + "/repos"
index_file_path = "../data/index.csv"

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

    head = re.compile("refs/heads/HEAD/.*")
    master = re.compile("refs/heads/master/.*")

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
                logger.debug("{} no found".format(file))
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
        refs = subprocess.run(["git", "show-ref"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode()

        matches = head.findall(refs)
        if not matches:
            logger.debug("No HEAD matches")
            matches = master.findall(refs)
            if not matches:
                logger.debug("No master matches")
                try:
                    matches = no_heads(refs)[-1]
                except IndexError:
                    matches = None

        if not matches:
            logger.error("No match for a head in {} {} with file {}".format(author, name, biggest_siva))
            logger.debug("Changing dir to {}".format(wd))
            os.chdir(wd)
            logger.info("Cleaning created directory")
            shutil.rmtree("{repo_path}/{author}/{name}/".format(repo_path=repos_path, author=author, name=name),
                          ignore_errors=True)
            continue

        ref = matches[-1]
        logger.debug("Newest head reference {}".format(ref))
        # git checkout ref
        logger.info("Checking out reference")
        subprocess.run(["git", "checkout", ref], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        logger.debug("Changing dir to {}".format(wd))
        os.chdir(wd)
        logger.debug("Cleaning .git directory")
        shutil.rmtree(repo_dir, ignore_errors=True)
