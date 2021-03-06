import sys
import json

import yaml

# outer
INFO_TEMPLATE = '''
FORMAT: 1A
HOST: {host}{basePath}

# {title}

{description}

> Version: {version}
'''.strip('\n')  # info & groups

# each group (#)
GROUP_TEMPLATE = '''
# Group {group}

{routes}
'''.strip('\n')

# each route (##)
ROUTE_TEMPLATE = '''
## {summary} [{route}]

{methods}
'''.strip('\n')

# each route method info (GET - xxx)
METHOD_INFO_TEMPLATE = '''
> {method} `{route}` - {summary} {description}
'''.strip('\n')  # req & resp

# each route method demo (###)
METHOD_DEMO_TEMPLATE = '''
### {summary} [{method}]
'''.strip('\n')  # req & resp


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


def pretty_json(obj: str) -> str:
    # noinspection PyBroadException
    try:
        return json.dumps(json.loads(obj), indent=4)
    except:
        return ''


def indent(content: str, size: int) -> str:
    """
    make multiline have an indent
    """
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        lines[idx] = size * ' ' + line
    return '\n'.join(lines)


def strcat(src: str, new: str, new_line_cnt: int = 0) -> str:
    """
    concat string with blank lines
    """
    src = src.strip('\n')
    new = new.strip('\n')
    bls = (new_line_cnt + 1) * '\n'
    return src + bls + new


def field(obj: {}, *names: str):
    out = obj
    for name in names:
        if name in out:
            out = out[name]
        else:
            return ''
    return out


def tmpl_main(obj: {}) -> str:
    service_info = field(field(obj, 'info', 'termsOfService'))
    license_info = md_url(field(obj, 'info', 'license', 'name'), field(obj, 'info', 'license', 'url'))
    contact_info = md_url(field(obj, 'info', 'contact', 'name'), field(obj, 'info', 'contact', 'url'),
                          other=field(obj, 'info', 'contact', 'email'))
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
    info = strcat(info, service_info)
    info = strcat(info, license_info)
    info = strcat(info, contact_info)
    return info


def prehandle_paths(paths: {}) -> {}:
    """
    parse paths dict to "group -> route -> method"
    """
    groups = {}
    for route, route_obj in paths.items():
        for method, method_obj in route_obj.items():
            tab = 'Default' if len(method_obj['tags']) == 0 else method_obj['tags'][0]
            if tab not in groups:
                groups[tab] = {}
            if route not in groups[tab]:
                groups[tab][route] = {}
            groups[tab][route][method] = method_obj
    return groups


def tmpl_model(def_obj: {}, token: str, is_req: bool, *, prefix: str = 'body') -> str:
    """
    parse #/definitions/xxx for request or response param
    """
    token = token.split('/')[-1]
    if token not in def_obj:
        return ''
    obj = def_obj[token]
    if 'properties' not in obj:
        return ''
    if 'required' not in obj:
        obj['required'] = []
    ret = ''
    if is_req:
        # in: `name` (type) req - desc (empty) (def)
        for prop, po in obj['properties'].items():
            p_type = po['type']
            p_desc = po['description']
            p_req = 'required' if prop in obj['required'] else 'not required'
            p_def = f' (default: {po["default"]})' if 'default' in po else ''
            if 'allowEmptyValue' in po:
                p_empty = ' (allow empty)' if po['allowEmptyValue'] else ' (not empty)'
            else:
                p_empty = ''
            ret = strcat(ret, f'+ `{prefix}` : `{prop}` ({p_type}) {p_req} - {p_desc}{p_empty}{p_def}')
            if 'enum' in po:
                ret = strcat(ret, indent(f'+ enum: {po["enum"]}', 4))
            nest_type = ''
            if p_type == 'object':
                nest_type = po['$ref']
            elif p_type == 'array':
                nest_type = po['items']['$ref']
            if nest_type != '':
                nest_tmpl = tmpl_model(def_obj, nest_type, is_req, prefix=prop).strip('\n')
                ret = strcat(ret, indent(nest_tmpl, 4))
    else:
        # in: `name` (type) - desc (empty) (example)
        for prop, po in obj['properties'].items():
            p_type = po['type']
            p_desc = po['description']
            p_ex = f' (example: {po["example"]})' if 'example' in po else ''
            if 'allowEmptyValue' in po:
                p_empty = ' (allow empty)' if po['allowEmptyValue'] else ' (not empty)'
            else:
                p_empty = ''
            ret = strcat(ret, f'+ `{prefix}` : `{prop}` ({p_type}) - {p_desc}{p_empty}{p_ex}')
            if 'enum' in po:
                ret = strcat(ret, indent(f'+ enum: {po["enum"]}', 4))
            nest_type = ''
            if p_type == 'object':
                nest_type = po['$ref']
            elif p_type == 'array':
                nest_type = po['items']['$ref']
            if nest_type != '':
                nest_tmpl = tmpl_model(def_obj, nest_type, is_req, prefix=prop).strip('\n')
                ret = strcat(ret, indent(nest_tmpl, 4))
    return ret


def tmpl_ctrl(groups_obj: {}, def_obj: {}) -> str:
    def parse_method_info(route: str, method: str, obj: {}) -> str:
        # -> GET - Summary
        tmpl = METHOD_INFO_TEMPLATE.format(
            method=method.upper(),
            route=route,
            summary=obj['summary'],
            description=f'({obj["description"]})' if 'description' in obj else ''
        ).strip(' ')

        req = ''
        resp = ''
        # Req Param
        if 'parameters' in obj:
            req = strcat(req, f'+ Request Parameter', 1)
            for idx, param in enumerate(obj['parameters']):
                p_name, p_in, p_desc = param['name'], param['in'], param['description']
                if 'type' in param:
                    p_type = param['type']
                elif 'schema' in param:
                    nest_type = tmpl_model(def_obj, param['schema']['$ref'], True)
                    if nest_type != '':
                        req = strcat(req, indent(nest_type, 4), 1 if idx == 0 else 0)
                    continue
                else:
                    p_type = 'unknown'
                p_req = 'required' if param['required'] else 'not required'
                p_def = f' (default: {param["default"]})' if 'default' in param else ''
                if 'allowEmptyValue' in param:
                    p_empty = ' (allow empty)' if param['allowEmptyValue'] else ' (not empty)'
                else:
                    p_empty = ''
                req_param = f'+ `{p_in}` : `{p_name}` ({p_type}) {p_req} - {p_desc}{p_empty}{p_def}'
                req = strcat(req, indent(req_param, 4), 1 if idx == 0 else 0)
                if 'enum' in param:
                    req = strcat(req, indent(f'+ enum: {param["enum"]}', 8))

        # Resp 200
        if 'responses' in obj:
            codes = [int(c) for c in obj['responses'].keys()]
            codes = [str(c) for c in sorted(codes)]
            for code in codes:
                resp_obj = obj['responses'][code]
                # Resp Desc
                if 'description' in resp_obj:
                    resp = strcat(resp, f'+ Response {code}', 1)
                    resp_desc = '+ ' + resp_obj['description']
                    resp_desc = indent(resp_desc, 4)
                    resp = strcat(resp, resp_desc, 1)
                # Resp Header
                if 'headers' in resp_obj:
                    headers_obj = {k: v for k, v in resp_obj['headers'].items() if k != 'Content-Type'}
                    if len(headers_obj) > 0:
                        resp = strcat(resp, f'+ Response {code} Header', 1)
                        for header, header_obj in headers_obj.items():
                            resp_header = f'+ `{header}` ({header_obj["type"]})'
                            resp_header = indent(resp_header, 4)
                            resp = strcat(resp, resp_header, 1)
                # Resp Body
                if 'schema' in resp_obj:
                    resp = strcat(resp, f'+ Response {code} Body', 1)
                    nest_type = tmpl_model(def_obj, resp_obj['schema']['$ref'], False)
                    if nest_type != '':
                        resp = strcat(resp, indent(nest_type, 4))
        tmpl = strcat(tmpl, req, 1)
        tmpl = strcat(tmpl, resp, 1)
        return tmpl

    def parse_method_demo(method: str, obj: {}) -> str:
        # -> ### Summary [GET]
        tmpl = METHOD_DEMO_TEMPLATE.format(
            summary=obj['summary'],
            method=method.upper()
        )
        req_codes = list(obj['requests'].keys()) if 'requests' in obj else []
        resp_codes = list(obj['responses'].keys()) if 'responses' in obj else []
        codes = [int(c) for c in req_codes + resp_codes]
        codes = [str(c) for c in sorted(set(codes))]
        for code in codes:
            req = ''
            resp = ''
            # Request 200
            if 'requests' in obj and code in obj['requests']:
                req = strcat(req, f'+ Request {code}', 1)
                req_obj = obj['requests'][code]
                # Header
                if 'headers' in req_obj:
                    req = strcat(req, indent('+ Headers', 4), 1)
                    for idx, (header, header_obj) in enumerate(req_obj['headers'].items()):
                        req_header = f'{header}: {header_obj["description"]}'
                        req_header = indent(req_header, 12)
                        req = strcat(req, req_header, 1 if idx == 0 else 0)
                # Body
                if 'examples' in req_obj:
                    req = strcat(req, indent('+ Body', 4), 1)
                    req_body = pretty_json(req_obj['examples']['application/json'])
                    req_body = indent(req_body, 12)
                    req = strcat(req, req_body, 1)

            # Response 200
            if 'responses' in obj and code in obj['responses']:
                resp = strcat(resp, f'+ Response {code}', 1)
                resp_obj = obj['responses'][code]
                # Header
                if 'headers' in resp_obj:
                    resp = strcat(resp, indent('+ Headers', 4), 1)
                    for header, header_obj in resp_obj['headers'].items():
                        resp_header = f'{header}: {header_obj["description"]}'
                        resp_header = indent(resp_header, 12)
                        resp = strcat(resp, resp_header, 1)
                # Body
                if 'examples' in resp_obj:
                    resp = strcat(resp, indent('+ Body', 4), 1)
                    resp_body = pretty_json(resp_obj['examples']['application/json'])
                    resp_body = indent(resp_body, 12)
                    resp = strcat(resp, resp_body, 1)
            tmpl = strcat(tmpl, req, 1)
            tmpl = strcat(tmpl, resp, 1)
        return tmpl

    def parse_route(route: str, route_obj: {}) -> str:
        """
        parse at '/v1/xxx': {'get': {xxx}}
        """
        method_infos = ''
        method_demos = ''
        for method, method_obj in route_obj.items():
            method_info = parse_method_info(route, method, method_obj)
            method_demo = parse_method_demo(method, method_obj)
            method_infos = strcat(method_infos, method_info, 1)
            method_demos = strcat(method_demos, method_demo, 1)
        ret = ''
        ret = strcat(ret, method_infos, 1)
        ret = strcat(ret, method_demos, 1)
        return ret

    out = ''
    for group, group_obj in groups_obj.items():
        # -> # Group
        routes = ''
        for route, route_obj in group_obj.items():
            # -> ## Route [xxx]
            summary = [method_obj['summary'] for method_obj in route_obj.values()]
            summary = ' & '.join(summary)
            methods = parse_route(route, route_obj)
            tmpl = ROUTE_TEMPLATE.format(
                summary=summary,
                route=route,
                methods=methods
            )
            routes = strcat(routes, tmpl, 1)

        tmpl = GROUP_TEMPLATE.format(
            group=group,
            routes=routes
        )
        out = strcat(out, tmpl, 1)
    return out


def run(yaml_name, apib_output):
    # noinspection PyBroadException
    try:
        print(f'> Reading {yaml_name}...')
        content = open(yaml_name, 'r', encoding='utf-8').read()
    except:
        print(f'Error: failed to open file {yaml_name}.')
        sys.exit(1)

    spec = yaml.load(content, Loader=yaml.FullLoader)

    # !!
    apib = tmpl_main(spec)
    groups_obj = prehandle_paths(spec['paths'])
    apib = strcat(apib, tmpl_ctrl(groups_obj, spec['definitions']), 1)

    apib_len = len(apib)
    while True:
        apib = apib.replace('\n\n\n', '\n\n')
        if apib_len != len(apib):
            apib_len = len(apib)
        else:
            break
    apib += '\n'

    # noinspection PyBroadException
    try:
        print(f'> Saving {apib_output}...')
        with open(apib_output, 'w', encoding='utf-8') as f:
            f.write(apib)
    except Exception as e:
        print(f'Error: failed to save file {apib_output}.{e}')
        sys.exit(1)


class Apib:

    def __init__(self, args):
        run(args.yaml_output, args.apib_output)
