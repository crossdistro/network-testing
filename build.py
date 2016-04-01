#! /usr/bin/env python3

import os
import json
import shutil

import click

SOURCE_FILES = {
    'schema': 'test-client-server-schema.json',
    'results': 'test-client-server.json',
}

def load_json(filename):
    with open(filename, encoding='utf-8') as file:
        return json.load(file)

@click.command()
@click.option('-o', '--outdir', default='./output/')
@click.option('--datadir', default='./data/')
@click.option('--templatedir', default='./templates/')
def build(datadir, outdir, templatedir):
    shutil.rmtree(outdir)
    os.makedirs(outdir)

    data = {ident: load_json(os.path.join(datadir, filename))
            for ident, filename in SOURCE_FILES.items()}

    print(data)


if __name__ == '__main__':
    build()
