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
'''.trim('\n')  # info groups

# each group (#)
GROUP_TEMPLATE = '''
# Group {group}

{routes}
'''.trim('\n')

# each route (##)
ROUTE_TEMPLATE = '''
## {summary} [{route}]
'''.trim('\n') # method demo

# each route method info (GET - xxx)
METHOD_INFO_TEMPLATE = '''
{method} - {summary} {description}
'''  # req resp

# each route method demo (###)
METHOD_DEMO_TEMPLATE = '''
### {summary} [{method}]
'''.trim('\n')  # req resp


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
    def parse_route(route_obj) -> str:
        """
        parse at '/v1/xxx': {'get': {xxx}}
        """
        ret = ''
        # Method Infos
        for method, obj in route_obj.items():
            # -> GET - Summary
            tmpl = METHOD_INFO_TEMPLATE.format(
                method=method.upper(),
                summary=obj['summary'],
                description=obj['description']
            )
            req = ''
            resp = ''
            # Req Param
            req = cat_newline(req, f'+ Request Parameter', 1)
            for param in obj['parameters']:
                req_param = f'`{param["name"]}` ({param["type"]} {param["in"]})' + \
                    f'{"required" if param["required"] else "not required"} - {param["description"]}'
                if 'allowEmptyValue' in param:
                    req_param += ' (allow empty)'
                if 'default' in param:
                    req_param += f' (default: {param["default"]})'
                req = cat_newline(req, f'+ {req_param}', 1)
            # Resp 200
            for code, resp_obj in obj['response'].items():
                desc = resp_obj['description']
                headers = resp_obj['headers']
                schema = resp_obj['schema']
                # Resp Desc
                if desc != '':
                    resp = cat_newline(resp, f'+ Response {code}', 1)
                    resp = cat_newline(resp, desc, 1)
                # Resp Header
                if headers is not None and len(headers) != 0:
                    resp = cat_newline(resp, f'+ Response {code} Header', 1)
                    for header, header_obj in headers.items():
                        header_tip = header + ' - ' + header_obj["description"]
                        resp = cat_newline(resp, header_tip, 1)
                # Resp Body
                if schema is not None:
                    resp = cat_newline(resp, f'+ Response {code} Body', 1)
                    model_name = schema['$ref'].trim('#/definitions/')
                    resp = cat_newline(resp, f'See {model_name}', 1)
            ret = cat_newline(ret, tmpl, 1)
            ret = cat_newline(ret, req, 1)
            ret = cat_newline(ret, resp, 1)

        # Method Demos
        for method, method_obj in route_obj.items():
            # -> ### Summary [GET]
            tmpl = METHOD_DEMO_TEMPLATE.format(
                summary=method_obj['summary'],
                method=method.upper()
            )
            demos = ''
            codes = list(method_obj['requests'].keys()) + list(method_obj['responses'].keys())
            codes = list(set(codes))
            for code in codes:
                req = ''
                resp = ''
                # Request 200
                if code in method_obj['requests']:
                    req = cat_newline(req, f'+ Request {code}', 1)
                    # Header
                    headers_obj = code['headers']
                    if headers_obj is not None and len(headers_obj) != 0:
                        req = cat_newline(req, indent_string('+ Headers', 4), 1)
                        for header, header_obj in headers_obj.items():
                            header_str = indent_string(header + ': ' + header_obj['description'], 12)
                            req = cat_newline(req, header_str, 1)
                    # Body
                    example_obj = code['examples']
                    if example_obj is not None:
                        req = cat_newline(req, indent_string('+ Body', 4), 1)
                        json_str = example_obj['application/json']
                        req = cat_newline(req, indent_string(json_str, 12), 1)

                # Response 200
                if code in method_obj['responses']:
                    resp = cat_newline(resp, f'+ Response {code}', 1)
                    # Header
                    headers_obj = code['headers']
                    if headers_obj is not None and len(headers_obj) != 0:
                        resp = cat_newline(resp, indent_string('+ Headers', 4), 1)
                        for header, header_obj in headers_obj.items():
                            header_str = indent_string(header + ': ' + header_obj['description'], 12)
                            resp = cat_newline(resp, header_str, 1)
                    # Body
                    example_obj = code['examples']
                    if example_obj is not None:
                        resp = cat_newline(resp, indent_string('+ Body', 4), 1)
                        resp = cat_newline(resp, indent_string(example_obj['application/json'], 12), 1)
                demos = cat_newline(demos, req, 1)
                demos = cat_newline(demos, resp, 1)
            ret = cat_newline(ret, tmpl, 1)
            ret = cat_newline(ret, demos, 1)
        return ret

    groups = ''
    for group, group_obj in groups.items():
        # -> # Group
        routes = ''
        for route, route_obj in group_obj.items():
            # -> ## Route [xxx]
            summary = [method_obj['summary'] for method_obj in route_obj.values()]
            summary = ' & '.join(summary)
            tmpl = ROUTE_TEMPLATE.format(
                summary=summary,
                route=route
            )
            methods = parse_route(route_obj)
            routes = cat_newline(routes, tmpl, 1)
            routes = cat_newline(routes, methods, 1)
        groups = cat_newline(groups, routes, 1)
    return groups


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str,
                        required=True, help='path of input yaml file')
    parser.add_argument('-o', '--output', type=str,
                        required=True, help='path of output html file')
    args = parser.parse_args()
    return args


def main():
    args = parse()
    try:
        print(f'> Reading {args.input}...')
        content = open(args.input, 'r', encoding='utf-8').read()
    except:
        print(f'Error: failed to open file {args.input}.')
        exit(1)
        return

    spec = yaml.load(content, Loader=yaml.FullLoader)

    # !!
    apib = tmpl_main(spec)
    groups_obj = prehandle(spec['paths'])
    apib = cat_newlines(apib, tmpl_ctrl(groups_obj), 1)
    print(apib)
    # try:
    #     print(f'> Saving {args.output}...')
    #     with open(args.output, 'w') as f:
    #         f.write(html)
    # except:
    #     print(f'Error: failed to save file {args.output}.')
    #     exit(1)


if __name__ == "__main__":
    main()
