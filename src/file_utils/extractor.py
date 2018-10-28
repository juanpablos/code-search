import csv

file = "test.csv"

with open(file, encoding="utf-8") as f:
    reader = csv.reader(f)

    for line in reader:
        url = line[0].split('/')
        author = url[-2]
        repo = url[-1]

        langs = line[3].lower().split(',')

        extensions = []
        if 'java' in langs:
            extensions.append('java')
        if 'python' in langs:
            extensions.append('py')

        if not extensions:
            continue

        # change dir to author/repo
        # list all files
        # search for extensions
        # write in index | java | python
        # copy-move | java dir | python dir
        # change dir to root
