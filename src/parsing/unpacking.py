import subprocess
import csv
import os
from itertools import repeat
import shutil

siva_path = "../../../../Go/siva/latest"
repos_path = siva_path + "/repos"

os.makedirs(repos_path, exist_ok=True)

with open("../data/index.csv") as f:
    index = csv.reader(f)

    for row in index:
        author = row[0].split('/')[-2]
        name = row[0].split('/')[-1]

        repo_dir = "{repo_path}/{author}/{name}/.git/".format(repo_path=repos_path, author=author, name=name)

        os.makedirs(repo_dir)

        siva_files = row[1].split(",")
        comp = dict(zip(siva_files, repeat(0, len(siva_files))))
        for file in siva_files:
            comp[file] = os.path.getsize("{path}/{hash}/{file}".format(path=siva_path, hash=file[:2], file=file))

        biggest_siva = max(comp.items(), key=lambda x: x[1])[0]
        biggest_path = "{path}/{hash}/{file}".format(path=siva_path, hash=biggest_siva[:2], file=biggest_siva)

        subprocess.run(["siva", "unpack", biggest_path, repo_dir])

        wd = os.getcwd()
        os.chdir(repos_path[-5])
        # choose a head ref to checkout
        # git show ref
        # git checkout ref
        shutil.rmtree(repo_dir, ignore_errors=True)
