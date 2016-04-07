#! /usr/bin/env python3

import os
import json
import shutil
import glob
import sys

import jinja2
import click
import yaml


SOURCE_FILES = {
    'results': 'results/*.json',
    'schema': 'test-client-server-schema.yaml',
    'result_colors': 'result-colors.yaml',
}

def load_file(filename):
    print('Loading', filename, file=sys.stderr)
    if filename.endswith('.json'):
        with open(filename, encoding='utf-8') as file:
            return json.load(file)
    elif filename.endswith('.yaml'):
        with open(filename, encoding='utf-8') as file:
            return yaml.safe_load(file)
    else:
        raise ValueError('Unknown extension: ' + filename)

def load_data(filename_base):
    if '*' in filename_base:
        result = {}
        filenames = glob.glob(filename_base)
        if not filenames:
            raise FileNotFoundError(filename_base)
        for filename in filenames:
            data = load_file(filename)
            try:
                data = dict(data)
            except ValueError:
                raise ValueError('Data needs to be a mapping: ', filename)
            if not data.keys().isdisjoint(result.keys()):
                raise ValueError('Overwriting data: ', filename)
            result.update(data)
        return result
    else:
        return load_file(filename_base)

base_path = os.path.dirname(__file__)

@click.command()
@click.option('-d', '--datadir', default=os.path.join(base_path, 'example_data/'),
              help='Directory containing input data (defaults to included example data)')
@click.option('-o', '--outdir', default=os.path.join(base_path, 'output/'),
              help='Directory for output (will be overwritten)')
@click.option('--templatedir', default=os.path.join(base_path, 'templates/'),
              help='Directory containing HTML templates')
def build(datadir, outdir, templatedir):
    try:
        shutil.rmtree(outdir)
    except FileNotFoundError:
        pass
    os.makedirs(outdir)

    data = {ident: load_data(os.path.join(datadir, filename))
            for ident, filename in SOURCE_FILES.items()}

    loader = jinja2.FileSystemLoader(templatedir)
    template_env = jinja2.Environment(
        loader=loader,
        undefined=jinja2.StrictUndefined,
        )

    def render(out_name, template_name, **env):
        template = template_env.get_template(template_name)
        result = template.render(data=data, **env)
        with open(os.path.join(outdir, out_name), 'w') as file:
            file.write(result)

    # Render all the pages
    render('index.html', 'index.html')

    print('Wrote to', os.path.abspath(outdir))


if __name__ == '__main__':
    build()
