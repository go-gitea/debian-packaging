#!/usr/bin/env python
'''
Purpose:   Build a Swagger-like documentation page for the Gitea API.
Reason:    Swagger-UI has over 750 JS libs that would require individual
           packaging, review, and maintenance.
           Ref: https://wiki.debian.org/Javascript/Nodejs/Tasks/swagger-ui
Copyright: Michael Lustfield (MTecknology)
License:   Expat with exclusions for MIT and Apache-2.0
Upstream:  https://github.com/MTecknology/static_swagger-ui
Env Vars:  SWAGGER_DST : Output destination, will overwrite existing files
           SWAGGER_SRC : Source JSON file
'''
import json
import os
import sys
import textwrap

if sys.version_info.major >= 3:
    from urllib.request import urlretrieve
else:
    from urllib import urlretrieve


class Templates(object):
    '''Big object to store the not-so-pretty template stuff.'''
    page = textwrap.dedent('''\
            <!DOCTYPE html><html><head>
              <meta charset="UTF-8">
              <title>{title}</title>
              <link rel="shortcut icon" href="/img/favicon.png" />
              {css}
            </head><body>
              <div class="wrapper">
                <h1>{title}</h1>
                <h2>[ Version: {version} | Base URL: {baseurl} ]</h2>
                <h3>{description}</h3>
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

    api_route = textwrap.dedent('''\
            <div class="opblock-section opblock-{api_method}">
              <a id="section-{section_id}" href="#" onclick="toggle_opbody(this.id); return false;">
                <div class="opblock-summary">
                  <span class="opblock-summary-method summary-{api_method}">{api_method}</span>
                  <span class="opblock-summary-path">{api_path}</span>
                  <span class="opblock-summary-description summary-model">{api_desc}</span>
                </div>
              </a>
              <div class="opblock-body" style="display: none;" id="opbod-section-{section_id}">
                {subsections}
              </div>
            </div>
            ''')

    api_model = textwrap.dedent('''\
            <div class="opblock-section opblock-model">
              <a id="model-{section_id}" href="#" onclick="toggle_opbody(this.id); return false;">
                <div class="opblock-summary">
                  <span class="opblock-summary-title summary-model">{api_title}</span>
                  <span class="opblock-summary-description summary-model">{api_desc}</span>
                </div>
              </a>
              <div class="opblock-body" style="display: none;" id="opbod-model-{section_id}">
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
              <td class="pcol-name">{name}</td>
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
                        border-radius: 3px; text-shadow: 0 1px 0 rgba(0,0,0,.1); }
              .opblock-summary-method { border-radius: 3px; text-align: center;
                        padding: 6px 15px; min-width: 80px; color: #ffffff; font-weight: 700; }
              .opblock-summary-path { font-size: 16px; display: flex; flex: 0 3 auto; word-break: break-all;
                        padding: 0 10px; font-family: monospace; font-weight: 600; }
              .opblock-summary-description { font-size: 13px; }
              .opblock-header { margin: 0 -20px; display: flex; align-items: center; min-height: 50px;
                        background: hsla(0,0%,100%,.8); box-shadow: 0 1px 2px rgba(0,0,0,.1); }
              .opblock-header:first-child { margin-top: -20px; }
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
              .opblock-body { padding: 20px; }
              .opblock-table { padding: 20px 0; }
              .opblock-table:last-child { padding-bottom: 0; }
              #tag-section-Models > .opblock-model { background:rgba(0,0,0,.05); }
              .opblock-model { border:1px solid rgba(59,65,81,.3); }
              .opblock-summary-title { padding: 6px; font-weight: 700; }
              .opblock-model .opblock-summary-description { padding: 0 10px 0 4px; }
              .opblock-model .opblock-body { border-top:1px solid rgba(59,65,81,.3); }
              table { width: 100%; padding: 0 10px; border-collapse: collapse; }
              th { font-size: 12px; padding: 0 0 12px; text-align: left;
                        border-bottom: 1px solid rgba(59,65,81,.2); }
              td { width: 30%; padding: 10px 0; vertical-align: top; }
              .red { color: #ff0000; }
              .blue { color: #5555aa; }
              .grey { color: #999999; }
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
    json_data = read_json()
    page_data = render_page(json_data)
    write_static(page_data)


def read_json(path='swagger.v1.json'):
    '''Read JSON input from file.'''
    src = os.environ.get('SWAGGER_SRC', path)
    return json.load(open(src, 'r'))


def write_static(page, destination='swagger.html'):
    '''Generate a Swagger-like HTML page.
    Returns: True for write success | False for failure.'''
    dest = os.environ.get('SWAGGER_DST', destination)
    try:
        with open(dest, 'w') as fh:
            fh.write(page)
    except:
        return False
    return True


def render_page(json_data):
    '''Assemble the entire page.'''
    for attr in ['description', 'title', 'license', 'version']:
        if attr not in json_data['info']:
            print('JSON data is missing required data: info:{}'.format(attr))
            return False
    info = json_data['info']
    baseurl = json_data['basePath']
    api_routes = build_routes(json_data)
    api_models = build_models(json_data)

    return Templates.page.format(**{
        'js': Templates.static_js,
        'css': Templates.static_css,
        'title': info['title'],
        'version': info['version'],
        'baseurl': baseurl,
        'description': info['description'],
        'api_body': api_routes + api_models})


def build_models(json_data):
    '''Build the HTML for a list of models.'''
    if not json_data.get('definitions', False):
        print('JSON data is missing required data: definitions')
        return False

    api_d = ''
    model_id = 0
    for model in sorted(json_data['definitions'].keys()):
        model_id += 1
        model_desc, subsections = build_model(json_data, model)
        if model_desc.startswith(model):
            model_desc = model_desc.replace(model, '', 1).strip().capitalize()
        api_d += Templates.api_model.format(**{
            'api_title': model,
            'api_desc': model_desc,
            'subsections': subsections,
            'section_id': '{}'.format(model_id)})

    return Templates.section.format(**{
        'title': 'Models',
        'api_d': api_d})


def build_model(json_data, model):
    '''Build the HTML for a model.'''
    if not model in json_data.get('definitions', []):
        print('Requested key "{}" not found in JSON data.'.format(model))
        return False
    mod = json_data['definitions'][model]
    mod_desc = mod.get('description', '')

    if 'properties' not in mod:
        return mod_desc, '<table class="parameters"><tr><td>No properties</tr></td></table>'

    rows = ''
    for prop, attr in sorted(mod['properties'].items()):
        if '$ref' in attr:
            description = 'Model: {}'.format(attr['$ref'].split('/')[-1])
        else:
            fmt = ' (' + attr['format'] + ')' if attr.get('format', '') else ''
            description = '{}<br />{}<br />{}'.format(
                '<span class="blue">{}{}</span>'.format(attr.get('type', 'undef'), fmt),
                '<span class="grey">x-go-name: {}</span>'.format(attr.get('x-go-name', 'undef')),
                attr.get('description', ''))

        rows += Templates.resp_row.format(**{
            'name': prop,
            'desc': description})

    return mod_desc, Templates.table.format(**{
        'headers': '',
        'table_rows': rows})


def build_routes(json_data):
    '''Build the API docs portion of the page.'''
    if not json_data.get('paths', ''):
        print('JSON data is missing required data: paths')
        return False
    paths = json_data['paths']
    topics = gen_topics(paths)

    sb = ''
    section_id = 0
    for tag, routes in sorted(topics.items()):
        section_id += 1
        api_d = build_route(json_data, routes, section_id)
        sb += Templates.section.format(**{
            'title': tag,
            'api_d': api_d})
    return sb

def build_route(json_data, keys, section_id=0):
    '''Build the HTML for a list (keys) of available API queries.'''
    paths = json_data['paths']

    # Attempt to sort by group, then length, then path+method
    keys.sort(key=lambda k: k[0:3] + str(len(k.split('^^')[0])) + k)

    sb = ''
    key_id = 0
    for key in keys:
        key_id += 1
        path, method = key.split('^^')
        desc = paths[path][method].get('summary', '')
        parameters = build_parameter_table(paths[path][method])
        responses = build_responses_table(paths[path][method], json_data)
        sb += Templates.api_route.format(**{
            'api_path': path,
            'api_desc': desc,
            'api_method': method,
            'subsections': str(parameters + responses),
            'section_id': '{}-{}'.format(section_id, key_id)})
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


def build_parameter_table(api):
    '''Build and return a table of parameters for an API method.'''
    if 'parameters' not in api:
        return '<table class="parameters"><tr><td>No parameters</tr></td></table>'

    rows = ''
    for row in sorted(api['parameters'], key=lambda k: k['name']):
        description = row.get('description', '')
        required = ' <span class="red">*</span>' if row.get('required', False) else ''
        if 'type' in row:
            vartype = row['type']
        elif 'type' in row.get('schema', {}):
            vartype = row['schema']['type']
        else:
            vartype = 'undefined'
        rows += Templates.param_row.format(**{
            'name': row['name'] + required,
            'desc': description,
            'type': vartype})

    table = Templates.table.format(**{
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
    for code, row in sorted(api['responses'].items()):
        description = find_response(row['$ref'], json_data) if '$ref' in row else ''
        rows += Templates.resp_row.format(**{
            'name': code,
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
    '''Lazy way to make sure we have a copy of test data.'''
    out = os.environ.get('SWAGGER_DST', output)
    src = os.environ.get('SWAGGER_URL', url)
    if not os.path.exists(out):
        urlretrieve(src, out)


if __name__ == '__main__':
    if not os.environ.get('SWAGGER_DST', ''):
        os.environ['SWAGGER_DST'] = 'swagger.html'
    if not os.environ.get('SWAGGER_SRC', ''):
        os.environ['SWAGGER_SRC'] = 'swagger.v1.json'
    main()
