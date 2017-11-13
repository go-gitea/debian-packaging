#!/usr/bin/env python
'''
Purpose:   Build a Swagger-like documentation page for the Gitea API.
Reason:    Swagger-UI has over 750 JS libs that would require individual
           packaging, review, and maintenance.
           Ref: https://wiki.debian.org/Javascript/Nodejs/Tasks/swagger-ui
Copyright: Michael Lustfield (MTecknology)
License:   Expat
           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:
           .
           The above copyright notice and this permission notice shall be included in
           all copies or substantial portions of the Software.
           .
           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
           IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
           FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
           AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
           LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
           OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
           THE SOFTWARE.
Testing:   Get json:: python -c 'import swagger_build; swagger_build.download_json()'
           Override:: export SWAGGER_DST='swaggerui.html' SWAGGER_SRC='swagger.v1.json'
           Build::    ./swagger_build.py
'''
import json
import os
import sys
import textwrap


class Templates(object):
    '''Big object to store the not-so-pretty template stuff.'''
    page = textwrap.dedent('''\
            <!DOCTYPE html><html><head>
              <meta charset="UTF-8">
              <title>{title}</title>
              {css}
            </head><body>
              <div class="wrapper">
                <h1>{title}</h1>
                <h2>[ Version: {version} | Base URL: {baseurl} ]</h2>
                <h3>{description}</h3>
                <p>Produced by a hacky script to avoid Swagger-UI dependencies.
                <br />Ref: <a href="https://wiki.debian.org/Javascript/Nodejs/Tasks/swagger-ui">https://wiki.debian.org/Javascript/Nodejs/Tasks/swagger-ui</a></p>
                {api_body}
                {js}
              </div>
            </body></html>
            ''')

    section = textwrap.dedent('''\
            <div class="tag-section">
              <a id="{title}" href="#" onclick="toggle_section(this.id); return false;">
                <h4 class="opblock-tag">{title}</h4>
              </a>
              <div id="tag-section-{title}">
              {api_d}
            </div>
            ''')

    path = textwrap.dedent('''\
            <div class="opblock-section opblock-{api_method}">
              <a id="{api_method}-{api_path}" href="#" onclick="toggle_opbody(this.id); return false;">
                <div class="opblock-summary">
                  <span class="opblock-summary-method summary-{api_method}">{api_method}</span>
                  <span class="opblock-summary-path">{api_path}</span>
                </div>
              </a>
              <div class="opblock-body" style="display: none;" id="opbod-{api_method}-{api_path}">
                {subsections}
              </div>
            </div>
            ''')

    subsect_div = textwrap.dedent('''\
            <div class="opblock-header"><h5>{header}</h5></div>
            <div class="opblock-table">
              {table}
            </div>
            ''')

    table = textwrap.dedent('''\
            <table class="parameters">
              <thead>
                {headers}
              </thead>
              <tbody>
                {table_rows}
              </tbody>
            </table>
            ''')

    param_row = textwrap.dedent('''\
            <tr>
              <td class="pcol-name">{name}</td>
              <td class="pcol-type">{type}</td>
              <td class="pcol-desc">{desc}</td>
            </tr>
            ''')

    resp_row = textwrap.dedent('''\
            <tr>
              <td class="pcol-name">{code}</td>
              <td class="pcol-desc">{desc}</td>
            </tr>
            ''')

    static_css = textwrap.dedent('''\
            <style>
              html { box-sizing: border-box; }
              *, *:before, *:after { box-sizing: inherit; }
              body { margin: 0; background-color: #fafafa; }
              .wrapper { width: 100%; max-width: 1460px; margin: 0 auto; padding: 15px 20px;
                        font-family: sans-serif; font-size: 14px; color: #3b4151; }
              h1 { font-size: 36px; margin: 0; }
              h2 { font-family: monospace; font-size: 12px; font-weight: 300; }
              h3 { font-size: 14px; }
              h4 { font-size: 24px; border-bottom: 1px solid rgba(59,65,81,.3);
                        padding: 10px; margin: 0 0 5px; cursor: pointer; }
              h5 { font-size: 12px; padding: 20px; margin: 0; }
              .tag-section a { text-decoration: inherit; color: inherit; cursor: pointer; }
              .tag-section a:focus, .opblock-section a:focus { outline: 0; }
              .opblock-section { margin: 0 0 15px; border: 1px solid; border-radius: 4px;
                        box-shadow: 0 0 3px rgba(0,0,0,.19); }
              .opblock-summary { display: flex; padding: 5px; align-items: center;
                        font-weight: 700; border-radius: 3px; text-shadow: 0 1px 0 rgba(0,0,0,.1); }
              .opblock-summary-method { padding: 6px 15px; border-radius: 3px; text-align: center;
                        padding: 6px 15px; min-width: 80px; color: #ffffff; }
              .opblock-summary-path { font-size: 16px; display: flex; flex: 0 3 auto; word-break: break-all;
                        padding: 0 10px; font-family: monospace; font-weight: 600; }
              .opblock-header { display: flex; align-items: center;  min-height: 50px;
                        background: hsla(0,0%,100%,.8); box-shadow: 0 1px 2px rgba(0,0,0,.1); }
              .opblock-post { border-color: #49cc90; background: rgba(73,204,144,.1); }
              .opblock-delete { border-color: #f93e3e; background: rgba(249,62,62,.1); }
              .opblock-get { border-color: #61affe; background: rgba(97,175,254,.1); }
              .opblock-patch { border-color: #50e3c2; background: rgba(80,227,194,.1); }
              .opblock-put { border-color: #fca130; background: rgba(252,161,48,.1); }
              .opblock-post .opblock-body { border-top: 1px solid #49cc90; }
              .opblock-delete .opblock-body { border-top: 1px solid #f93e3e; }
              .opblock-get .opblock-body { border-top: 1px solid #61affe; }
              .opblock-patch .opblock-body { border-top: 1px solid #50e3c2; }
              .opblock-put .opblock-body { border-top: 1px solid #fca130; }
              .summary-post { background: #49cc90; }
              .summary-get { background: #61affe; }
              .summary-delete { background: #f93e3e; }
              .summary-patch { background: #50e3c2; }
              .summary-put { background: #fca130; }
              .opblock-table { padding: 20px 20px 10px; }
              table { width: 100%; padding: 0 10px; border-collapse: collapse; }
              th { font-size: 12px; padding: 0 0 12px; text-align: left;
                        border-bottom: 1px solid rgba(59,65,81,.2); }
              td { max-width: 20%; min-width: 6em; padding: 10px 0; vertical-align: top; }
            </style>
            ''')

    static_js = textwrap.dedent('''\
            <script type="text/javascript">
              function toggle_opbody(name_id) {
                toggle("opbod-" + name_id);
              }
              function toggle_section(name_id) {
                toggle("tag-section-" + name_id);
              }
              function toggle(tgt) {
                if (document.getElementById(tgt).style.display == "none") {
                  document.getElementById(tgt).style.display = "block";
                } else {
                  document.getElementById(tgt).style.display = "none";
                }
              }
            </script>
            ''')


def die(msg=None, exit_code=1):
    '''Print a message if provided and exit with a non-zero status.'''
    if not msg:
        msg = 'Unknown failure.'
    print('** FATAL: {} **\n'.format(msg))
    sys.exit(exit_code)


def main():
    '''Read a JSON file and turn it into a static page.'''
    data = read_json()
    if not data:
        die('Unable to read JSON data from file.')
    write_static(data)


def read_json(path='public/swagger.v1.json'):
    '''Read JSON input from file.'''
    src = os.environ.get('SWAGGER_SRC', path)
    try:
        j = json.load(open(path, 'r'))
    except:
        return None
    return j


def write_static(json_data, destination='templates/swagger.tmpl'):
    '''Generate a Swagger-like HTML page.'''
    for attr in ['info', 'basePath', 'paths']:
        if attr not in json_data:
            die('JSON data is missing required data: {}.'.format(attr))

    dest = os.environ.get('SWAGGER_DST', destination)

    try:
        with open(dest, 'w') as fh:
            fh.write(build_page(json_data))
    except IOError:
        die('Unable to create output destination: {}'.format(dest))


def build_page(json_data):
    '''Assemble the entire page.'''
    info = json_data['info']
    baseurl = json_data['basePath']
    for attr in ['description', 'title', 'license', 'version']:
        if attr not in info:
            die('JSON data is missing required data: {}.'.format(attr))

    api_body = build_body(json_data)

    return Templates.page.format(**{
        'js': Templates.static_js,
        'css': Templates.static_css,
        'title': info['title'],
        'version': info['version'],
        'baseurl': baseurl,
        'description': info['description'],
        'api_body': api_body})


def build_body(json_data):
    '''Build the API docs portion of the page.'''
    paths = json_data['paths']
    topics = gen_topics(paths)
    sb = ''
    for k, v in topics.items():
        api_d = build_section(json_data, v)
        sb += Templates.section.format(**{
            'title': k,
            'api_d': api_d})
    return sb


def gen_topics(paths):
    '''Read tags and paths and build the data for topics display.'''
    tags = {}
    for path, methods in paths.items():
        for method, attrs in methods.items():
            if 'tags' not in attrs:
                continue
            for tag in attrs['tags']:
                t = '{}^^{}'.format(path, method)
                if tag not in tags:
                    tags[tag] = []
                if t not in tags[tag]:
                    tags[tag].append(t)
    return tags


def build_section(json_data, keys):
    '''Build a HTML for a list (keys) of available API queries.'''
    paths = json_data['paths']
    sb = ''
    for key in keys:
        path, method = key.split('^^')
        parameters = build_parameter_table(paths[path][method])
        responses = build_responses_table(paths[path][method], json_data)
        sb += Templates.path.format(**{
            'api_path': path,
            'api_method': method,
            'subsections': str(parameters + responses)})
    return sb


def build_parameter_table(api):
    '''Build and return a table of parameters for an API method.'''
    if 'parameters' not in api:
        return '<table class="parameters"><tr><td>No parameters</tr></td></table>'

    rows = ''
    for row in api['parameters']:
        description = row['description'] if 'description' in row else ''
        if 'type' in row:
            vartype = row['type']
        elif 'schema' in row and 'type' in row['schema']:
            vartype = row['schema']['type']
        else:
            vartype = 'undefined'
        rows += Templates.param_row.format(**{
            'name': row['name'],
            'desc': description,
            'type': vartype})

    table =  Templates.table.format(**{
        'headers': '<th>Name</th><th>Type</th><th>Description</th>',
        'table_rows': rows})

    return Templates.subsect_div.format(**{
        'header': 'Parameters',
        'table': table})


def build_responses_table(api, json_data):
    '''Build and return a table of response codes to expect from this API query.'''
    if 'responses' not in api:
        return ''

    rows = ''
    for code, row in api['responses'].items():
        description = find_response(row['$ref'], json_data) if '$ref' in row else ''
        rows += Templates.resp_row.format(**{
            'code': code,
            'desc': description})

    table = Templates.table.format(**{
        'headers': '<th>Code</th><th>Description</th>',
        'table_rows': rows})

    return Templates.subsect_div.format(**{
        'header': 'Responses',
        'table': table})


def find_response(needle, haystack):
    '''Find and return a response description from JSON data.'''
    if 'responses' not in haystack:
        return ''
    n = needle.split('/')[-1]
    if n in haystack['responses'] and 'description' in haystack['responses'][n]:
        return haystack['responses'][n]['description']
    return ''


def download_json(url='https://try.gitea.io/swagger.v1.json', output='swagger.v1.json'):
    '''Lazy way to make sure we have a copy of test data.
    This should be used only for testing purposes.'''
    import urllib2
    if not os.path.exists(output):
        response = urllib2.urlopen(url)
        html = response.read()
        with open(output, 'w') as fh:
            fh.write(html)


if __name__ == '__main__':
    main()
