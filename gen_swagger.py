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
    pass


def literal_presenter(dumper, data):
    # https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(Literal, literal_presenter)


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


def gen_files(all_file_paths: [], *, demo_model: {}, template: {}) -> ({}, {}):
    """
    Generate apis and models from all files
    :return: paths, defs
    """
    paths = {}
    defs = {}
    for file_path in all_file_paths:
        try:
            file_content = open(file_path, 'r', encoding='utf-8').read()
        except:
            print(f'Error: failed to open file {file_path}.')
            exit(1)
            return

        flag = '// @Router'
        content_sp = file_content.split(flag)
        if len(content_sp) > 1:
            for content in content_sp:
                en = file_content.index(content)
                st = en - len(flag)
                if st < 0:
                    continue
                if file_content[st:en] != flag:
                    continue
                content = '\n' + flag + content
                router, method, obj = gen_ctrl(content, demo_model=demo_model, template=template)
                if obj is not None:
                    if router not in paths:
                        paths[router] = {}
                    paths[router][method] = obj

        flag = '// @Model'
        content_sp = file_content.split(flag)
        if len(content_sp) > 1:
            for content in content_sp:
                en = file_content.index(content)
                st = en - len(flag)
                if st < 0:
                    continue
                if file_content[st:en] != flag:
                    continue
                content = '\n' + flag + content
                model_name, model_po = gen_model(content)
                if model_po is not None:
                    defs[model_name] = model_po

    return paths, defs


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
            pname, pin, ptype, preq, pempty, *pother = split_bs(param)
            pname, pin, ptype = trim(pname), trim(pin), trim(ptype)
            preq, pempty = trim(preq.lower()), trim(pempty.lower())

            pother = trim(' '.join(pother))
            pother_sp = re.compile(r'"(.*)"(.*)').findall(pother)
            pdesc = trim(pother_sp[0][0])
            pdefault = trim(pother_sp[0][1])

            obj = {
                'name': pname,
                'in': pin,
                'type': ptype,  # x
                'required': preq == 'true',
                'allowEmptyValue': pempty == 'true',
                'description': pdesc
            }
            if pdefault != '':
                if ptype == 'integer':
                    pdefault = int(pdefault)
                obj['default'] = pdefault  # x

            obj_ptn = re.compile(r'#(.+)')
            obj_name = obj_ptn.findall(ptype)
            if len(obj_name) != 0:
                obj_name = trim(obj_name[0])
                del obj['type']
                if 'default' in obj:
                    del obj['default']
                obj['schema'] = {
                    '$ref': f'#/definitions/{obj_name}'
                }

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

        def replace_demo_model(content: str, demo_model: {}) -> str:
            if demo_model is not None:
                for dm in re.compile(r'\${(.+?)}').findall(content):
                    if dm not in demo_model:
                        continue
                    try:
                        new_dm = json.dumps(demo_model[dm])  # <<
                        content = content.replace('${%s}' % dm, new_dm)
                    except:
                        pass
            return content

        # Desc
        resp_desc_arr = []
        read_tmpl(resp_desc_arr, 'ResponseDesc')
        resp_desc_arr.extend(split_array(tokens, 'ResponseDesc'))
        for desc in resp_desc_arr:
            rcode, *rmsg = split_bs(desc)
            rmsg = ' '.join(rmsg)
            rmsg = replace_demo_model(rmsg, demo_model)
            if rcode in responses and 'description' in responses[rcode]:
                rmsg = responses[rcode]['description'] + ', ' + rmsg
            if rcode not in responses:
                responses[rcode] = {}
            responses[rcode]['description'] = Literal(rmsg)

        # Header
        resp_header_arr = []
        read_tmpl(resp_header_arr, 'ResponseHeader')
        resp_header_arr.extend(split_array(tokens, 'ResponseHeader'))
        for hdr in resp_header_arr:
            rcode, *rheader = split_bs(hdr)
            rheader = ' '.join(rheader)
            rheader = replace_demo_model(rheader, demo_model)
            rheader = json.loads(rheader)

            if rcode not in responses:
                responses[rcode] = {}
            if 'headers' not in responses[rcode]:
                responses[rcode]['headers'] = {}
            for k, v in rheader.items():
                responses[rcode]['headers'][k] = {
                    'type': 'string',
                    'description': v
                }

        # Body
        resp_example_arr = []
        read_tmpl(resp_example_arr, 'Response')
        resp_example_arr.extend(split_array(tokens, 'Response'))
        for resp in resp_example_arr:
            rcode, *rjson = split_bs(resp)
            rjson = trim(' '.join(rjson))
            rjson = replace_demo_model(rjson, demo_model)
            rjson = json.dumps(json.loads(rjson), indent=4, ensure_ascii=False)
            if rcode not in responses:
                responses[rcode] = {}
            responses[rcode]['example'] = Literal(rjson)

        obj = {
            'operationId': oid,
            'summary': field(kv, 'Summary'),
            'description': field(kv, 'Description', required=False),
            'tags': tags,
            'consumes': accepts,
            'produces': produces,
            'parameters': parameters,
            'security': securities,
            'responses': responses
        }
        return router, method, obj
    except:
        # traceback.print_exc()
        return '', '', None


def gen_model(content: str) -> (str, {}):
    """
    Generate definition doc from a model
    :return: name, obj
    """
    try:
        tokens = parse_content(content)
        kv = split_dict(tokens)

        # @Model LoginParam "parameter of login"
        # @Property username string true true "name of user" example

        # meta
        model = field(kv, 'Model')
        model_sp = split_bs(model)
        title = trim(model_sp[0])
        description = trim(' '.join(model_sp[1:])).strip('"')

        # prop
        prop_po = {}
        requires = []
        props = split_array(tokens, 'Property')
        for prop in props:
            pname, ptype, preq, pempty, *pother = split_bs(prop)
            pname, ptype, preq, pempty = trim(pname), trim(ptype), trim(preq) == "true", trim(pempty) == "true"
            pother = trim(' '.join(pother))
            pother_sp = re.compile(r'"(.*)"(.*)').findall(pother)
            pdesc = trim(pother_sp[0][0])
            pexample = trim(pother_sp[0][1])

            if preq:
                requires.append(pname)
            obj = {
                'description': pdesc,
                'type': ptype,
                'allowEmptyValue': pempty,
                'example': pexample
            }
            if pexample != '':
                if ptype == 'integer':
                    obj['example'] = int(pexample)

            obj_ptn = re.compile(r'#(.+)')
            obj_name = obj_ptn.findall(ptype)
            if len(obj_name) != 0:
                obj_name = trim(obj_name[0])
                del obj['type']
                del obj['example']
                obj['$ref'] = f'#/definitions/{obj_name}'

            prop_po[pname] = obj

        obj = {
            'title': title,
            'description': description,
            'type': 'object',
            'required': requires,
            'properties': prop_po
        }
        return title, obj
    except:
        # traceback.print_exc()
        return '', None


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
    paths, defs = gen_files(all_files, demo_model=demo_model, template=template)
    out['paths'] = paths
    out['definitions'] = defs

    # save
    out = stripper(out)
    print(f'> Saving {args.output}...')
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(out, stream=f, encoding='utf-8', allow_unicode=True)
    except:
        print(f'Error: failed to save file {args.output}.')
        exit(1)


if __name__ == '__main__':
    main()
