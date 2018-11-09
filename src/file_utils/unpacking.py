import csv
import logging
import os
import re
import shutil
import subprocess
import sys

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

siva_path = "./siva/latest"
repos_path = "./repositories"
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
        url = row[0]
        author = url.split('/')[-2]
        name = url.split('/')[-1]
        logger.info("Unpacking {} {}".format(author, name))

        siva_files = row[1].split(",")

        # create dir
        repo_dir = "{repo_path}/{author}/{name}".format(repo_path=repos_path, author=author, name=name)
        logger.debug("Creating path {}".format(repo_dir))
        os.makedirs(repo_dir)

        for siva in siva_files:
            siva_file_path = "{path}/{hash}/{file}".format(path=siva_path, hash=siva[:2], file=siva)
            siva_extract_path = repo_dir + "/{}/.git".format(siva.split(".")[0])

            # extract to author/repo/<siva>/.git
            logger.debug("Extracting {} to {}".format(siva, siva_extract_path))
            logger.debug("Extracting {}".format(siva))
            if os.path.exists(siva_file_path):
                subprocess.run(["siva", "unpack", siva_file_path, siva_extract_path], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                logger.warning("Siva file not found".format(siva_file_path))
                logger.debug("Skipping")
                continue

            # search for /refs/heads/HEAD
            logger.debug("Checking existence of HEAD references in siva")
            if not os.path.isdir(siva_extract_path + "/refs/heads/HEAD"):
                # if not found delete whole <siva>
                logger.info("No HEAD reference found, continuing")
                logger.debug("Removing siva repo {}".format(siva.split(".")[0]))
                shutil.rmtree(repo_dir + "/{}".format(siva.split(".")[0]), ignore_errors=True)
                logger.debug("Skipping siva")
                continue

        # assert only one <siva> remains -> error
        logger.debug("Calculating number of siva files with HEAD references")
        head_sivas = os.listdir(repo_dir)
        if len(head_sivas) > 1:
            logger.critical(
                "More than one siva file with HEAD for repository {}/{} ({})".format(author, name, len(head_sivas)))
            logger.critical("Siva files with HEADs {}".format(head_sivas))
            logger.info("Skipping")
            logger.debug("Removing {}".format(repo_dir))
            shutil.rmtree(repo_dir, ignore_errors=True)
            continue
        elif len(head_sivas) == 0:
            logger.critical("No siva file with HEAD for repository {}/{}".format(author, name))
            logger.info("Skipping")
            logger.debug("Removing {}".format(repo_dir))
            shutil.rmtree(repo_dir, ignore_errors=True)
            continue
        else:
            logger.debug("Only one siva file with HEAD references found")
            siva = head_sivas[0]
            # count files in HEAD
            logger.debug("Listing number of HEAD references")
            refs = os.listdir(repo_dir + "/{}/.git/refs/heads/HEAD".format(siva))

            wd = os.getcwd()
            logger.debug("Changing dir to {}".format(repo_dir + "/{}/".format(siva)))
            os.chdir(repo_dir + "/{}/".format(siva))

            if len(refs) > 1:
                logger.info("More than one reference found ({})".format(len(refs)))
                # open config/remotes and search for <url>, then corresponding <ref>
                # git remote -v to get pair <reference> <url>
                remotes = subprocess.check_output(["git", "remote", "-v"]).decode('utf-8')
                ref = re.search(r'.*{}'.format(url), remotes, re.MULTILINE).group(0).split('\t')[0]
                if not ref:
                    logger.critical(
                        "No HEAD reference found for siva file {} in repository {}/{}".format(siva, author, name))
                    logger.critical("No reference found for url {}".format(url))

                    logger.debug("Changing dir to {}".format(wd))
                    os.chdir(wd)

                    logger.debug("Removing {}".format(repo_dir))
                    shutil.rmtree(repo_dir, ignore_errors=True)
                    continue

                logger.debug("Found reference {} for url {}".format(ref, url))
            else:
                logger.debug("Found a single reference")
                ref = refs[0]

            logger.info("Found reference {}".format(ref))

            # checkout <ref>
            logger.info("Checking out reference")
            subprocess.run(["git", "checkout", "refs/heads/HEAD/{}".format(ref)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

            logger.debug("Changing dir to {}".format(wd))
            os.chdir(wd)
            # rm .git
            logger.debug("Cleaning .git directory")
            shutil.rmtree(repo_dir + "/{}/.git".format(siva), ignore_errors=True)
            # mv author/repo/<siva>/* to author/repo/
            logger.info("Moving files from siva directory to repository")
            logger.debug("Moving dir {} to {}".format(repo_dir + "/{}".format(siva), repo_dir))
            src = repo_dir + "/{}/".format(siva)
            for content in os.listdir(src):
                shutil.move(src + content, repo_dir)
            # rm siva directory
            logger.debug("Cleaning siva directory")
            shutil.rmtree(repo_dir + "/{}/".format(siva), ignore_errors=True)
