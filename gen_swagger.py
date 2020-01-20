import argparse
import os
import re
import json
import yaml


def trim(content: str) -> str:
    return content.strip(' \t')


def stripper(data):
    new_data = {}
    for k, v in data.items():
        if isinstance(v, dict):
            v = stripper(v)
        if not v in (u'', None, {}, []):
            new_data[k] = v
    return new_data


class literal(str):
    @staticmethod
    def literal_presenter(dumper, data):
        # https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')


def parse_content(content) -> []:
    """
    Parse token in one line or multi lines
    // @xxx xxx, // @xxx, /* @xxx xxx */, /* @xxx */
    """
    one_line_ptn = re.compile(r'// @(.+)')
    multi_line_ptn = re.compile(r'/\* @(.+)\*/', re.DOTALL)
    tokens = one_line_ptn.findall(content)
    tokens.extend(multi_line_ptn.findall(content))
    return tokens


def split_kv(tokens: []) -> ([], []):
    """
    Split all tokens into key-value list
    ['x', 'y z', 'a b', 'a c'] ->
    ['x', 'y', 'a', 'a'], ['', 'z', 'b', 'c']
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
    Split tokens into single key-value dict
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
    Split tokens into array
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
    Generate swagger config from main file
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
        'swagger': '2.0',
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
            'version': field(kv, 'Version', required=False),
            'termsOfService': field(kv, 'TermsOfService'),
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
            router, method, obj = gen_ctrl(
                content, demo_resp=demo_resp, auth_param=auth_param, auth_ec=auth_ec)
            if obj is not None:
                if router not in paths:
                    paths[router] = {}
                paths[router][method] = obj

    return paths


def gen_ctrl(content: str, *, demo_resp: {}, auth_param: [], auth_ec: []) -> (str, str, {}):
    """
    Generate api doc from a route
    :return: route, obj
    """
    try:
        tokens = parse_content(content)
        kv = split_dict(tokens)

        # meta
        router = field(kv, 'Router')
        router, *route_setting = re.split(r'[ \t]', router)
        method = route_setting[0][1:-1].lower()
        is_auth = len(route_setting) >= 2 and route_setting[1] == '[Auth]'
        oid = router.lower().replace(
            '/', '-').replace('{', '-').replace('}', '-').replace('?', '-') + '-' + method
        oid = oid.replace('--', '-')[1 if oid[0] == '-' else 0:]

        # arrays
        tags = split_array(tokens, 'Tag')
        accepts = split_array(tokens, 'Accept')
        accepts = accepts if len(accepts) != 0 else ['application/json']
        produces = split_array(tokens, 'Produce')
        produces = produces if len(produces) != 0 else ['application/json']

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

        # response
        responses = {}
        ec_arr = split_array(tokens, 'ErrorCode')
        if is_auth and auth_ec is not None:
            ec_arr.extend(auth_ec)
        for ec in ec_arr:
            ecode, *emsg = re.split(r'[ \t]', ec)
            emsg = '"{}"'.format(' '.join(emsg))
            if ecode in responses:
                emsg = '{}, {}'.format(responses[ecode]['description'], emsg)
            responses[ecode] = {
                'description': literal(emsg)
            }

        resp_arr = split_array(tokens, 'Response')
        for resp in resp_arr:
            rcode, *rjson = re.split(r'[ \t]', resp)
            rjson = ' '.join(rjson)
            rjson_demo = re.compile(r'\${(.+?)}').findall(rjson)
            for dm in rjson_demo:
                if demo_resp is not None and dm in demo_resp:
                    try:
                        rjson = rjson.replace(
                            '${%s}' % dm, json.dumps(demo_resp[dm]))
                    except:
                        pass
            rjson = json.dumps(json.loads(rjson), indent=4)
            rjson = f'```json\n{rjson}\n```'
            responses[rcode] = {
                'description': literal(rjson)
            }

        obj = {
            'operationId': oid,
            'summary': field(kv, 'Summary'),
            'description': field(kv, 'Description'),
            'tags': tags,
            'consumes': accepts,
            'produces': produces,
            'parameters': parameters,
            'responses': responses,
            'security': [{'basicAuth': ''}] if is_auth else []
        }
        return router, method, obj
    except:
        return '', '', None


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--main', type=str,
                        required=True, help='main file of swagger config')
    parser.add_argument('-o', '--output', type=str,
                        required=True, help='path of output yaml')
    parser.add_argument('-e', '--ext', type=str, nargs='*',
                        default=[], help='extension of files wanted to parse')
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
    out['paths'].update(paths)

    # save
    out = stripper(out)
    yaml.add_representer(literal, literal.literal_presenter)
    print(f'> Saving {args.output}...')
    with open(args.output, 'w', encoding='utf-8') as f:
        yaml.dump(out, stream=f, encoding='utf-8', allow_unicode=True)


if __name__ == '__main__':
    main()

# python ..\..\swagger_apib_gen\gen_swagger.py -m main.go -o a.yaml -e go
