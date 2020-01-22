import argparse
import os
import traceback
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
    Generate swagger config from main file
    """
    try:
        content = open(file_path, 'r', encoding='utf-8').read()
    except:
        print(f'Error: failed to open file {file_path}.')
        exit(1)

    tokens = parse_content(content)
    kv = split_dict(tokens)

    # @Template auth.Param sss
    # @Template auth.ErrorCode sss
    # @Template auth.ErrorCode sss2
    template_arr = split_array(tokens, 'Template')
    template = {}
    for tmpl in template_arr:
        tmpl_token = re.split(r'[ \t]', tmpl)
        if len(tmpl_token) <= 1:
            continue
        tmpl_content = trim(' '.join(tmpl_token[1:]))
        tmpl_type_sp = tmpl_token[0].split('.')
        tmpl_type = trim(tmpl_type_sp[0])
        tmpl_type_param = trim(' '.join(tmpl_type_sp[1:]))
        if tmpl_type not in template:
            template[tmpl_type] = {}
        if tmpl_type_param not in template[tmpl_type]:
            template[tmpl_type][tmpl_type_param] = []
        template[tmpl_type][tmpl_type_param].append(tmpl_content)

    out = {
        'swagger': '2.0',
        'host': field(kv, 'Host'),
        'basePath': field(kv, 'BasePath'),
        'demoModel': field(kv, 'DemoModel', required=False),
        'template': template,
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


def gen_ctrls(all_file_paths: [], *, demo_model: {}, template: {}) -> {}:
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
            router, method, obj = gen_ctrl(content, demo_model=demo_model, template=template)
            if obj is not None:
                if router not in paths:
                    paths[router] = {}
                paths[router][method] = obj

    return paths


def gen_ctrl(content: str, *, demo_model: {}, template: {}) -> (str, str, {}):
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
        oid = router.lower().replace('/', '-').replace('{', '-').replace('}', '-').replace('?', '-') + '-' + method
        oid = oid.replace('--', '-')[1 if oid[0] == '-' else 0:]

        # arrays
        tags = split_array(tokens, 'Tag')
        accepts = split_array(tokens, 'Accept')
        accepts = accepts if len(accepts) != 0 else ['application/json']
        produces = split_array(tokens, 'Produce')
        produces = produces if len(produces) != 0 else ['application/json']

        # template
        templates = field(kv, 'Template', required=False)
        templates = [trim(t) for t in templates.split(',')] if templates != '' else []

        def read_tmpl(out: [], token: str):
            for tmpl_type, tmpl_po in template.items():
                if tmpl_type not in templates:
                    continue
                if token in tmpl_po:
                    out.extend(tmpl_po[token])
        is_auth = 'Auth' in templates

        # parameter
        parameters = []
        param_arr = []
        read_tmpl(param_arr, 'Param')
        param_arr.extend(split_array(tokens, 'Param'))

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
        ec_arr = []
        read_tmpl(ec_arr, 'ErrorCode')
        ec_arr.extend(split_array(tokens, 'ErrorCode'))
        for ec in ec_arr:
            ecode, *emsg = re.split(r'[ \t]', ec)
            emsg = '"{}"'.format(' '.join(emsg))
            if ecode in responses and 'description' in responses[ecode]:
                emsg = '{}, {}'.format(responses[ecode]['description'], emsg)

            responses[ecode] = {
                'description': literal(emsg)
            }

        resp_arr = []
        read_tmpl(resp_arr, 'Response')
        resp_arr.extend(split_array(tokens, 'Response'))
        for resp in resp_arr:
            rcode, *rcontent = re.split(r'[ \t]', resp)
            rcontent = ' '.join(rcontent)
            rcontent_demo = re.compile(r'\${(.+?)}').findall(rcontent)

            for dm in rcontent_demo:
                if demo_model is not None and dm in demo_model:
                    try:
                        rcontent = rcontent.replace('${%s}' % dm, json.dumps(demo_model[dm]))
                    except:
                        pass

            rheader_pattern = re.compile(r'{\|(.+?)\|}', re.DOTALL)
            rbody_pattern = re.compile(r'{(.+)}', re.DOTALL)
            rheaders = rheader_pattern.findall(rcontent)
            rheader = '' if len(rheaders) == 0 else rheaders[-1]
            rbodys = rbody_pattern.findall(rcontent)
            rbody = ''
            for i in range(len(rbodys) - 1, -1, -1):
                if rbodys[i][0] != '|' and rbodys[i][-1] != '|':
                    rbody = rbodys[i]
                    break
            rdesc = responses[rcode]['description'] if rcode in responses else ''

            # Header
            rheader = '{' + rheader + '}'
            try:
                rheader = json.loads(rheader)
                rheader_tmp = ''
                for k, v in rheader.items():
                    rheader_tmp += f'{k}: {v}\n'
                if len(rheader_tmp) != 0:
                    rheader_tmp = rheader_tmp[:-1]
                rheader = rheader_tmp
            except:
                rheader = ''

            if rheader != '':
                rheader = f'```json\n{rheader}\n```'
                if rdesc != '':
                    rdesc += '\n'
                rdesc += rheader

            # Body
            if rbody != '':
                try:
                    rbody = f'{{{rbody}}}'
                    rbody = json.dumps(json.loads(rbody), indent=4)
                    rbody = f'```json\n{rbody}\n```'
                    if rdesc != '':
                        rdesc += '\n'
                    rdesc += rbody
                except:
                    pass
            responses[rcode] = {
                'description': literal(rdesc)
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
        traceback.print_exc()
        return '', '', None


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
            demo_model = json.loads(open(out['demoModel'], 'r', encoding='utf-8').read())
        except:
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
    out['paths'].update(paths)

    # save
    out = stripper(out)
    yaml.add_representer(literal, literal.literal_presenter)
    print(f'> Saving {args.output}...')
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(out, stream=f, encoding='utf-8', allow_unicode=True)
    except:
        print(f'Error: failed to save file {args.output}.')
        exit(1)


if __name__ == '__main__':
    main()
