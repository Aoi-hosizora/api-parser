import argparse
import ast
import json
import os
import re
import traceback

import jsonref
import yaml


def trim(content: str) -> str:
    return content.strip(' \t\n')


def split_bs(content: str) -> []:
    return list(filter(None, re.split(r'[ \t]', content)))


def stripper(data):
    new_data = {}
    for k, v in data.items():
        if isinstance(v, dict):
            v = stripper(v)
        if v not in (u'', None, {}, []):
            new_data[k] = v
    return new_data


class Literal(str):
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
        sp = split_bs(token)
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


def split_array(tokens: [], array_field: str) -> []:
    """
    ['a b', 'a c'] -> ['b', 'c']
    """
    ks, vs = split_kv(tokens)
    arr = []
    for idx in range(len(ks)):
        k, v = ks[idx], vs[idx]
        if k == array_field:
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
        return

    tokens = parse_content(content)
    kv = split_dict(tokens)

    # @Template auth.Param sss
    # @Template auth.ErrorCode sss
    # @Template auth.ErrorCode sss2
    template_arr = split_array(tokens, 'Template')
    template = {}
    for tmpl in template_arr:
        tmpl_token = split_bs(tmpl)
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

    # @Tag "Authorization" "Auth-Controller"
    tag_po = []
    tags = split_array(tokens, 'Tag')
    for tag in tags:
        tag_sp = re.compile(r'"(.+?)"').findall(tag)
        if len(tag_sp) < 2:
            continue
        tag_po.append({
            'name': trim(tag_sp[0]),
            'description': tag_sp[1]
        })

    # @GlobalSecurity Jwt Authorization header
    securities_po = {}
    securities = split_array(tokens, 'GlobalSecurity')
    for sec in securities:
        sec_sp = split_bs(sec)
        if len(sec_sp) != 3:
            continue
        sec_type = trim(sec_sp[0])
        securities_po[sec_type] = {
            'type': 'apiKey',
            'name': trim(sec_sp[1]),
            'in': trim(sec_sp[2])
        }

    out = {
        'swagger': '2.0',
        'host': field(kv, 'Host'),
        'basePath': field(kv, 'BasePath'),
        'demoModel': field(kv, 'DemoModel', required=False),
        'template': template,
        'tags': tag_po,
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
        'securityDefinitions': securities_po,
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
            return
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
        router, *route_setting = split_bs(router)
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
        templates = [trim(t) for t in split_bs(templates)] if templates != '' else []

        def read_tmpl(out: [], token: str):
            for tmpl_type, tmpl_po in template.items():
                if tmpl_type not in templates:
                    continue
                if token in tmpl_po:
                    out.extend(tmpl_po[token])

        # parameter
        parameters = []
        param_arr = []
        read_tmpl(param_arr, 'Param')
        param_arr.extend(split_array(tokens, 'Param'))

        for param in param_arr:
            pname, pin, ptype, preq, *pother = split_bs(param)
            pname, pin, ptype, preq = trim(pname), trim(pin), trim(ptype), trim(preq.lower())
            pother = ' '.join(pother)
            pother_sp = re.compile(r'"(.+?)"(.*)').findall(pother)
            pdesc = trim(pother_sp[0][0])
            pdefault = trim(pother_sp[0][1])
            obj = {
                'name': pname,
                'in': pin,
                'type': ptype,
                'required': preq == 'true',
                'description': pdesc
            }
            if pdefault != '':
                if ptype == 'integer':
                    pdefault = int(pdefault)
                obj['default'] = pdefault
            parameters.append(obj)

        # security
        securities = []
        sec_fields = split_array(tokens, 'Security')
        for sec in sec_fields:
            securities.append({
                sec: []
            })

        # response
        responses = {}
        ec_arr = []
        read_tmpl(ec_arr, 'ErrorCode')
        ec_arr.extend(split_array(tokens, 'ErrorCode'))
        for ec in ec_arr:
            ecode, *emsg = split_bs(ec)
            emsg = ' '.join(emsg)
            emsg = f'"{emsg}"'
            if ecode in responses and 'description' in responses[ecode]:
                emsg = responses[ecode]['description'] + ', ' + emsg

            responses[ecode] = {
                'description': Literal(emsg)
            }

        resp_arr = []
        read_tmpl(resp_arr, 'Response')
        resp_arr.extend(split_array(tokens, 'Response'))
        for resp in resp_arr:
            rcode, *rcontent = split_bs(resp)
            rcontent = trim(' '.join(rcontent))

            if demo_model is not None:
                for dm in re.compile(r'\${(.+?)}').findall(rcontent):
                    if dm not in demo_model:
                        continue
                    try:
                        new_dm = json.dumps(demo_model[dm])  # <<
                        rcontent = rcontent.replace('${%s}' % dm, new_dm)
                    except:
                        pass

            rheader_pattern = re.compile(r'{\|(.+)\|}', re.DOTALL)
            rbody_pattern = re.compile(r'{([^|].*[^|]*)}', re.DOTALL)
            rcontent = rcontent.replace('{}', '{ }')

            rheaders = rheader_pattern.findall(rcontent)
            rheader = '' if len(rheaders) == 0 else rheaders[-1]
            rbodys = rbody_pattern.findall(rcontent)
            rbody = '' if len(rbodys) == 0 else rbodys[-1]
            if rcode in responses:
                rdesc = responses[rcode]['description']
            else:
                rdesc = ''

            # Header
            if rheader != '':
                rheader = '{' + rheader + '}'
                try:
                    rheader_tmp = ''
                    rheader = json.loads(rheader)
                    for k, v in rheader.items():
                        rheader_tmp += f'{k}: {v}\n'
                    rheader = trim(rheader_tmp)

                    if rheader != '':
                        if rdesc != '':
                            rdesc += '\n'
                        rdesc += f'```json\n{rheader}\n```'
                except:
                    pass

            # Body
            if rbody != '':
                try:
                    rbody = '{' + rbody + '}'
                    rbody = json.dumps(json.loads(rbody), indent=4)

                    if rbody != '':
                        if rdesc != '':
                            rdesc += '\n'
                        rdesc += f'```json\n{rbody}\n```'
                except:
                    pass

            responses[rcode] = {
                'description': Literal(rdesc)
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
            'security': securities
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
    # https://json-spec.readthedocs.io/reference.html
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
    out['paths'].update(paths)

    # save
    out = stripper(out)
    yaml.add_representer(Literal, Literal.literal_presenter)
    print(f'> Saving {args.output}...')
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(out, stream=f, encoding='utf-8', allow_unicode=True)
    except:
        print(f'Error: failed to save file {args.output}.')
        exit(1)


if __name__ == '__main__':
    main()
