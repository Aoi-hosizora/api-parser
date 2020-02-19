import argparse
import ast
import os
import re
import json
import traceback

import jsonref

# outer
INFO_TEMPLATE = '''
FORMAT: 1A
HOST: {host}{basePath}

# {title}

{description}

> Version: {version}
''' # info groups

# each group (#)
GROUP_TEMPLATE = '''
# Group {group}

{routes}
'''

# each route (##)
ROUTE_TEMPLATE = '''
## {summary} [{route}]

{methods}

{demos}
'''

# each route method info (GET - xxx)
METHOD_TEMPLATE = '''
{method} - {summary} {description}
''' # req resp

# each demo (###)
DEMO_TEMPLATE = '''
### {summary} [{method}]

{codes}
'''

# each demo code (200)
DEMO_CODE_TEMPLATE = '''
+ Request {code}

    + Headers

{header}

    + Body

{body}
'''


def trim(content: str) -> str:
    return content.strip(' \t\n')


def md_url(name: str, url: str, *, other: str = '') -> str:
    ret = ''
    if name != '' and url == '':
        ret = name
    elif name == '' and url != '':
        ret = url
    elif name != '' and url != '':
        ret = f'[{name}]({url})'
    if other != '':
        if ret == '':
            ret = other
        else:
            ret = f'{ret} - {other}'
    return ret


def indent_string(indent: int, content: str) -> str:
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        lines[idx] = indent * ' ' + line
    return '\n'.join(lines)


def cat_newline(src: str, new: str, new_line_cnt: int = 0) -> str:
    src = trim(src)
    new = trim(new)
    bls = (new_line_cnt + 1) * '\n'
    return src + bls + new


def tmpl_main(obj: {}) -> str:
    service_info = obj['info']['termsOfService']
    license_info = md_url(obj['info']['license']['name'], obj['info']['license']['url'])
    contact_info = md_url(obj['info']['contact']['name'], obj['info']['contact']['url'], other=obj['info']['contact']['email'])
    if service_info != '':
        service_info = f'>\n> [Terms of services]({service_info})'
    if license_info != '':
        license_info = f'>\n> License: {license_info}'
    if contact_info != '':
        contact_info = f'>\n> Contact: {contact_info}'

    info = INFO_TEMPLATE.format(
        host=obj['host'],
        basePath=obj['basePath'],
        title=obj['info']['title'],
        description=obj['info']['description'],
        version=obj['info']['version']
    )
    info = cat_newline(info, service_info)
    info = cat_newline(info, license_info)
    info = cat_newline(info, contact_info)
    info = trim(info)


def prehandle_obj(obj: {}) -> {}:
    """
    parse paths dict to "group -> route -> method"
    """
    groups = {}
    for route, route_obj in obj['paths'].items():
        for method, method_obj in route_obj.items():
            this_groups = ['Default'] if len(method_obj['groups']) == 0 else method_obj['groups']
            for group in this_groups:
                if group not in groups:
                    groups[group] = {}
                if route not in groups[group]:
                    groups[group][route] = {}
                groups[group][route][method] = method_obj
    return groups

def tmpl_ctrl(groups: {}) -> str:
    for group, group_obj in groups.items():
        # -> # Group
        routes = ''
        for route, route_obj in group_obj.items():
            # -> ## Route [xxx]
            methods = ''
            for method, obj in route_obj.items():
                # -> GET - xxx
                # -> Request xxx
                req, resp = '', ''
                tmpl = METHOD_TEMPLATE.format(
                    method=method,
                    summary=obj['summary'],
                    description=obj['description']
                )
                pass
            demos = ''
            for method, method_obj in route_obj.items():
                # -> ### Route [GET]
                pass

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--main', type=str,
                        required=True, help='path of main file containing swagger config')
    parser.add_argument('-o', '--output', type=str,
                        required=True, help='path of output yaml')
    parser.add_argument('-e', '--ext', type=str, nargs='*',
                        default=[], help='extensions of files wanted to parse')
    args = parser.parse_args()
    return args


def main():
    args = parse()
    main_file = args.main
    all_files = [main_file]
    for root, _, files in os.walk('.'):
        for f in files:
            if len(args.ext) == 0 or f.split('.')[-1] in args.ext:
                all_files.append(os.path.join(root, f))

    # main
    print(f'> Parsing {main_file}...')
    out = gen_main(main_file)

    # demo response
    if out['demoModel'] != '':
        print(f'> Parsing {out["demoModel"]}...')
        try:
            demo_model = open(out['demoModel'], 'r', encoding='utf-8').read()
            demo_model = str(jsonref.loads(demo_model))
            demo_model = ast.literal_eval(demo_model)
        except:
            # traceback.print_exc()
            demo_model = None
        out['demoModel'] = ''
    else:
        demo_model = None

    # global template
    template = out['template']
    out['template'] = {}

    # ctrl
    print(f'> Parsing {main_file}...')
    paths = gen_ctrls(all_files, demo_model=demo_model, template=template)
    out['paths'] = paths

    # apib
    print(f'> Generate apib...')
    apib = gen_apib(out)

    # save
    print(f'> Saving {args.output}...')
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(apib)
    except:
        print(f'Error: failed to save file {args.output}.')
        exit(1)


if __name__ == '__main__':
    main()
