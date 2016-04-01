#! /usr/bin/env python3

import os
import json
import shutil

import jinja2
import click

SOURCE_FILES = {
    'schema': 'test-client-server-schema.json',
    'results': 'test-client-server.json',
    'result_colors': 'result-colors.json',
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

    render('index.html', 'index.html')

    print('Output is in:')
    print(os.path.abspath(outdir))


if __name__ == '__main__':
    build()
