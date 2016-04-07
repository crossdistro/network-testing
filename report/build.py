#! /usr/bin/env python3

"""Generate a HTML report based on network test output
"""

import os
import json
import shutil
import glob
import sys

import jinja2
import click
import yaml


STATIC_DATA_FILES = {
    'schema': 'test-client-server-schema.yaml',
    'result_colors': 'result-colors.yaml',
}

def load_data(filename):
    print('Loading', filename, file=sys.stderr)
    if filename.endswith('.json'):
        with open(filename, encoding='utf-8') as file:
            return json.load(file)
    elif filename.endswith('.yaml'):
        with open(filename, encoding='utf-8') as file:
            return yaml.safe_load(file)
    else:
        raise ValueError('Unknown extension: ' + filename)

base_path = os.path.dirname(__file__)

@click.command(help=__doc__)
@click.option('-s', '--staticdatadir', default=os.path.join(base_path, 'static_data/'),
              help='Alternate directory containing static data such as test descriptions')
@click.option('-o', '--outdir', default=os.path.join(base_path, 'output/'),
              help='Directory for output (will be overwritten)')
@click.option('--templatedir', default=os.path.join(base_path, 'templates/'),
              help='Directory containing HTML templates')
@click.argument('input_file', nargs=-1)
def build(staticdatadir, outdir, templatedir, input_file):
    if not input_file:
        raise click.UsageError('No files given. Try running: {} {}'.format(
              sys.argv[0], os.path.join(base_path, 'example_data/*')))
        print(__doc__, file=sys.stderr)
        print(file=sys.stderr)
        print('No files given. Try running:',
              sys.argv[0], os.path.join(base_path, 'example_data/*'),
              file=sys.stderr)
        return

    try:
        shutil.rmtree(outdir)
    except FileNotFoundError:
        pass
    os.makedirs(outdir)

    data = {ident: load_data(os.path.join(staticdatadir, filename))
            for ident, filename in STATIC_DATA_FILES.items()}
    data['results'] = results = {}
    for filename in input_file:
        result = load_data(filename)
        try:
            result = dict(result)
        except ValueError:
            raise ValueError('Data needs to be a mapping: ', filename)
        if not result.keys().isdisjoint(results.keys()):
            raise ValueError('Overwriting data: ', filename)
        results.update(result)

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
