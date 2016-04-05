#! /usr/bin/env python3

import os
import json
import shutil

import jinja2
import click
import yaml

SOURCE_FILES = {
    'schema': 'test-client-server-schema',
    'results': 'test-client-server',
    'result_colors': 'result-colors',
}

def load_data(filename_base):
    try:
        json_file = open(filename_base + '.json', encoding='utf-8')
    except FileNotFoundError:
        json_file = None
    try:
        yaml_file = open(filename_base + '.yaml', encoding='utf-8')
    except FileNotFoundError:
        yaml_file = None
    try:
        if json_file and yaml_file:
            raise ValueError(filename_base + ": both JSON and YAML exist")
        elif json_file:
            return json.load(json_file)
        elif yaml_file:
            return yaml.load(yaml_file)
        else:
            raise ValueError(filename_base + ": neither JSON nor YAML exist")
    finally:
        if json_file:
            json_file.close()
        if yaml_file:
            yaml_file.close()

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
