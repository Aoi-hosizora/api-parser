import argparse
import os
import re
import json
import traceback


def trim(content: str) -> str:
    return content.strip(' \t\n')


def parse_content(content) -> []:
    """
    // @xxx xxx, // @xxx, /* @xxx xxx */, /* @xxx */
    """
    one_line_ptn = re.compile(r'// @(.+)')
    multi_line_ptn = re.compile(r'/\* @(.+?)\*/', re.DOTALL)
    tokens = one_line_ptn.findall(content)
    tokens.extend(multi_line_ptn.findall(content))
    return tokens


def split_kv(tokens: []) -> ([], []):
    """
    ['x', 'y z', 'a b', 'a c'] -> ['x', 'y', 'a', 'a'], ['', 'z', 'b', 'c']
    """
    ks, vs = [], []
    for token in tokens:
        sp = re.split(r'[ \t]', token)
        val = ' '.join(sp[1:]) if len(sp) > 1 else ''
        ks.append(trim(sp[0]))
        vs.append(trim(val))
    return ks, vs


def split_dict(tokens: []) -> {}:
    """
    ['x', 'y z', 'a b', 'a c'] -> {'x': '', 'y': 'z'}
    """
    ks, vs = split_kv(tokens)
    kv = {}
    for idx in range(len(ks)):
        k, v = ks[idx], vs[idx]
        if ks.count(k) == 1:
            kv[k] = v
    return kv


def split_array(tokens: [], field: str) -> []:
    """
    ['a b', 'a c'] -> ['b', 'c']
    """
    ks, vs = split_kv(tokens)
    arr = []
    for idx in range(len(ks)):
        k, v = ks[idx], vs[idx]
        if k == field:
            arr.append(trim(v))
    return arr


def field(src: {}, src_field: str, *, required=True) -> str:
    """
    Get field in object dict
    """
    if src_field in src:
        return src[src_field]
    elif not required:
        return ''
    else:
        print(f'Error: don\'t contain required field: {src_field}')
        exit(1)


def gen_main(file_path: str) -> {}:
    """
    Generate config object from main file
    """
    try:
        content = open(file_path, 'r', encoding='utf-8').read()
    except:
        print(f'Error: failed to open file {file_path}.')
        exit(1)

    tokens = parse_content(content)
    kv = split_dict(tokens)
    auth_param = split_array(tokens, 'Authorization.Param')
    auth_error = split_array(tokens, 'Authorization.Error')

    out = {
        'host': field(kv, 'Host'),
        'basePath': field(kv, 'BasePath'),
        'demoResponse': field(kv, 'DemoResponse', required=False),
        'auth': {
            'param': auth_param,
            'error': auth_error
        },
        'info': {
            'title': field(kv, 'Title'),
            'description': field(kv, 'Description'),
            'version': field(kv, 'Version'),
            'termsOfService': field(kv, 'TermsOfService', required=False),
            'license': {
                'name': field(kv, 'License.Name', required=False),
                'url': field(kv, 'License.Url', required=False)
            },
            'contact': {
                'name': field(kv, 'Contact.Name', required=False),
                'url': field(kv, 'Contact.Url', required=False),
                'email': field(kv, 'Contact.Email', required=False)
            }
        },
        'paths': {}
    }
    return out


def gen_ctrls(all_file_paths: [], *, demo_resp: {}, auth_param: [], auth_ec: []) -> {}:
    """
    Generate apis doc from all files
    """
    paths = {}
    for file_path in all_file_paths:
        try:
            file_content = open(file_path, 'r', encoding='utf-8').read()
        except:
            print(f'Error: failed to open file {file_path}.')
            exit(1)
        flag = '// @Router'
        content_sp = file_content.split(flag)
        if len(content_sp) == 1:
            continue

        for content in content_sp:
            en = file_content.index(content)
            st = en - len(flag)
            if st < 0:
                continue
            # print(file_content[st:en])
            if file_content[st:en] != flag:
                continue

            content = '\n' + flag + content
            router, method, obj = gen_ctrl(content, demo_resp=demo_resp, auth_param=auth_param, auth_ec=auth_ec)
            if obj is not None:
                if router not in paths:
                    paths[router] = {}
                paths[router][method] = obj

    return paths


def gen_ctrl(content: str, *, demo_resp: {}, auth_param: [], auth_ec: []) -> (str, str, {}):
    """
    Generate api doc from a route
    :return: route, method, obj
    """
    try:
        tokens = parse_content(content)
        kv = split_dict(tokens)

        # meta
        router = field(kv, 'Router')
        router, *route_setting = re.split(r'[ \t]', router)
        method = route_setting[0][1:-1].lower()
        is_auth = len(route_setting) >= 2 and route_setting[1] == '[Auth]'
        groups = split_array(tokens, 'Group')
        groups.extend(split_array(tokens, 'Tag'))

        # parameter
        parameters = []
        param_arr = split_array(tokens, 'Param')
        if is_auth and auth_param is not None:
            param_arr.extend(auth_param)
        for param in param_arr:
            pname, pin, ptype, preq, *pdesc = re.split(r'[ \t]', param)
            pdesc = ' '.join(pdesc)[1:-1]
            preq = preq.lower() == 'true'
            parameters.append({
                'name': pname,
                'in': pin,
                'type': ptype,
                'required': preq,
                'description': pdesc
            })

        # errorCode
        errorCodes = {}
        ec_arr = split_array(tokens, 'ErrorCode')
        if is_auth and auth_ec is not None:
            ec_arr.extend(auth_ec)
        for ec in ec_arr:
            ecode, *emsg = re.split(r'[ \t]', ec)
            emsg = '"{}"'.format(' '.join(emsg))
            if ecode in errorCodes:
                emsg = '{}, {}'.format(errorCodes[ecode], emsg)
            errorCodes[ecode] = emsg

        """
        @Request 200    {|
                            "Content-Type": "application/json; charset=utf-8",
                            "Others": "xxx"
                        |} {
                            "ping": "pong"
                        }
        """
        def parse_req_resp(req_resp_arr: []) -> []:
            for r in req_resp_arr:
                rcode, *rcontent = re.split(r'[ \t]', r)
                rcontent = ' '.join(rcontent)
                rcontent_demo = re.compile(r'\${(.+?)}').findall(rcontent)
                for dm in rcontent_demo:
                    if demo_resp is not None and dm in demo_resp:
                        try:
                            rcontent = rcontent.replace('${%s}' % dm, json.dumps(demo_resp[dm]))
                        except:
                            pass

                rheader_pattern = re.compile(r'\{\|(.+?)\|\}', re.DOTALL)
                rbody_pattern = re.compile(r'\{(.+?)\}', re.DOTALL)
                rheaders = rheader_pattern.findall(rcontent)
                rheader = '' if len(rheaders) == 0 else rheaders[-1]
                rbodys = rbody_pattern.findall(rcontent)
                rbody = ''
                for i in range(len(rbodys) - 1, -1, -1):
                    if rbodys[i][0] != '|' and rbodys[i][-1] != '|':
                        rbody = rbodys[i]
                        break

                rheader = '{' + rheader + '}'
                try:
                    rheader = json.loads(rheader)
                    rheader_tmp = ''
                    if 'Content-Type' not in rheader:
                        rheader['Content-Type'] = 'application/json; charset=utf-8'
                    for k, v in rheader.items():
                        rheader_tmp += f'{k}: {v}\n'
                    if len(rheader_tmp) != 0:
                        rheader_tmp = rheader_tmp[:-1]
                    rheader = rheader_tmp
                except:
                    rheader = ''

                if rbody != '':
                    try:
                        rbody = '{' + rbody + '}'
                        rbody = json.dumps(json.loads(rbody), indent=4)
                    except:
                        rbody = ''

                yield {
                    'code': rcode,
                    'header': rheader,
                    'body': rbody
                }

        # code page
        codePages = {}

        req_arr = split_array(tokens, 'Request')
        resp_arr = split_array(tokens, 'Response')
        req_arr = list(parse_req_resp(req_arr))
        resp_arr = list(parse_req_resp(resp_arr))

        for req_po in req_arr:
            if req_po['code'] not in codePages:
                codePages[req_po['code']] = {}
            codePages[req_po['code']]['request'] = {
                'header': req_po['header'],
                'body': req_po['body']
            }
        for resp_po in resp_arr:
            if resp_po['code'] not in codePages:
                codePages[resp_po['code']] = {}
            codePages[resp_po['code']]['response'] = {
                'header': resp_po['header'],
                'body': resp_po['body']
            }

        obj = {
            'summary': field(kv, 'Summary'),
            'description': field(kv, 'Description'),
            'groups': groups,
            'parameters': parameters,
            'errorCodes': errorCodes,
            'codePages': codePages
        }

        return router, method, obj
    except Exception as ex:
        # traceback.print_exc()
        return '', '', None


def gen_apib(obj: {}) -> str:
    def md_url(name: str, url: str, *, other: str = '') -> str:
        name, url, other = trim(name), trim(url), trim(other)
        ret = ''
        if name != '' and url == '':
            ret = name
        elif name == '' and url != '':
            ret = url
        elif name != '' and url != '':
            ret = f'[{name}]({url})'
        if other != '':
            ret += (' - ' if ret != '' else '') + other
        return ret

    def cat_newline(src: str, new: str, cnt: int = 2) -> str:
        if new != '':
            bs = '\n' * cnt
            return f'{src}{bs}{new}'
        else:
            return src

    INFO_TEMPLATE = '''
FORMAT: 1A
HOST: {host}{basePath}

# {title}

{description}

> Version: {version}
'''

    license_info = md_url(obj['info']['license']['name'], obj['info']['license']['url'])
    contact_info = md_url(obj['info']['contact']['name'], obj['info']['contact']['url'], other=obj['info']['contact']['email'])
    service_info = obj['info']['termsOfService']
    service_info = f'>\n> [Terms of services]({service_info})' if service_info != '' else ''
    if license_info != '':
        license_info = '>\n> License: ' + license_info
    if contact_info != '':
        contact_info = '>\n> Contact: ' + contact_info

    info = INFO_TEMPLATE.format(title=obj['info']['title'], description=obj['info']['description'],
                                host=obj['host'], basePath=obj['basePath'], version=obj['info']['version'])
    info = trim(info)
    info = cat_newline(info, service_info, 1)
    info = cat_newline(info, license_info, 1)
    info = cat_newline(info, contact_info, 1)
    info = trim(info)

    paths = {}
    for path, pos in obj['paths'].items():
        for method, po in pos.items():
            group = 'Default' if len(po['groups']) == 0 else po['groups'][0]
            if group not in paths:
                paths[group] = {}
            if path not in paths[group]:
                paths[group][path] = {}
            paths[group][path][method] = po

    for group, group_po in paths.items():
        # every -> # Group
        info += '\n\n# Group ' + group
        for path, path_po in group_po.items():
            # every -> ## Summary [xxx]
            summaries = []
            method_page_str = []
            code_page_str = []
            for method, method_po in path_po.items():
                # every -> ### Description [GET]
                method = method.upper()
                summaries.append(method_po['summary'])

                # method page
                request_header = ''
                request_body = ''
                response_header = ''
                response_body = ''
                response_error = ''
                code_parameters = []

                def add_req_resp_hb(out: str, content: str, flag: str) -> str:
                    out = f'+ {flag}\n' if out == '' else out
                    out += '\n' + content
                    return out

                for param in method_po['parameters']:
                    param_content = ' ' * 4 \
                        + f'+ `{param["name"]} {param["type"]}` ' \
                        + ('required' if param['required'] else 'not required') + ' - ' + param['description']
                    if param['in'] == 'path':
                        param_type = param["type"]
                        if param_type == 'integer':
                            param_type = 'number'
                        code_parameters.append({
                            'name': param["name"],
                            'type': param_type
                        })
                    elif param['in'] == 'header':
                        request_header = add_req_resp_hb(request_header, param_content, 'Request Header')
                    elif param['in'] == 'response_header':
                        response_header = add_req_resp_hb(response_header, param_content, 'Response Header')
                    elif param['in'] == 'response_body':
                        response_body = add_req_resp_hb(response_body, param_content, 'Response Body')
                    else:
                        request_body = add_req_resp_hb(request_body, param_content, 'Request Body')

                if len(method_po['errorCodes']) != 0:
                    response_error = '+ Response Error\n'
                ecodes = sorted(method_po['errorCodes'].keys())
                for ecode in ecodes:
                    response_error += '\n' + ' ' * 4 + f'+ `{ecode}` - ' + method_po['errorCodes'][ecode]

                method_page = f'{method} - {method_po["description"]}'
                method_page = cat_newline(method_page, request_header)
                method_page = cat_newline(method_page, request_body)
                method_page = cat_newline(method_page, response_header)
                method_page = cat_newline(method_page, response_body)
                method_page = cat_newline(method_page, response_error)

                # code_page
                code_page = f'### {method_po["summary"]} [{method}]\n'
                code_page_po = method_po['codePages']
                codes = sorted(code_page_po.keys())

                def parse_code_page(flag: str, po: {}) -> str:
                    indent4 = '\n' + ' ' * 4
                    indent12 = '\n' + ' ' * 12
                    curr_code_page = f'\n+ {flag}\n' + indent4 + '+ Headers\n'
                    if len(po['header']) != 0:
                        header = po['header'].replace('\n', indent12)
                        curr_code_page += indent12 + header
                    curr_code_page += '\n' + indent4 + '+ Body\n'
                    if len(po['body']) != 0:
                        body = po['body'].replace('\n', indent12)
                        curr_code_page += indent12 + body
                    curr_code_page += '\n'
                    return curr_code_page

                if len(code_parameters) != 0:
                    code_page += '\n+ Parameters\n'
                    for param in code_parameters:
                        code_page += '\n' + ' '* 4 + '+ {} ({})'.format(param['name'], param['type'])
                    code_page += '\n'

                for code in codes:
                    code_po = code_page_po[code]
                    if 'request' in code_po:
                        code_page += parse_code_page('Request', code_po['request'])
                    if 'response' in code_po:
                        code_page += parse_code_page('Response ' + code, code_po['response'])

                method_page_str.append(method_page)
                code_page_str.append(code_page)

            summaries = ', '.join(summaries)
            method_page_str = '\n\n'.join(method_page_str)
            code_page_str = '\n\n'.join(code_page_str)

            info += '\n\n' + trim(f'''
## {summaries} [{path}]

{method_page_str}

{code_page_str}
''')
    # print(info)
    return info


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
    if out['demoResponse'] != '':
        print(f'> Parsing {out["demoResponse"]}...')
        try:
            demo_resp = json.loads(
                open(out['demoResponse'], 'r', encoding='utf-8').read())
        except:
            demo_resp = None
        out['demoResponse'] = ''
    else:
        demo_resp = None

    # global auth
    auth_param = out['auth']['param']
    auth_ec = out['auth']['error']
    out['auth'] = {}

    # ctrl
    print(f'> Parsing {main_file}...')
    paths = gen_ctrls(all_files, demo_resp=demo_resp,
                      auth_param=auth_param, auth_ec=auth_ec)
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
