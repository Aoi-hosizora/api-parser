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
    """
    split string through blackspace and tab (except in brackets)
    """
    bl_ptn = re.compile(r'\((.+?)\)')
    bls = bl_ptn.findall(content)
    for bl in bls:
        content = content.replace(bl, bl.replace(' ', ',,'))
    # replace blankspace to ,, in brackets first
    ret = list(filter(None, re.split(r'[ \t]', content)))
    return [trim(cnt.replace(',,', ' ')) for cnt in ret]


def split_comma(content: str) -> []:
    """
    split string through , (except \,)
    """
    # replace \, to ,, in first
    ctns = content.replace(',', ',,').replace('\\,,', ',').split(',,')
    return [trim(ctn) for ctn in ctns]


def stripper(dict_data, ex_key: []):
    """
    strip dict list and set
    :param dict_data:
    :param ex_key: except keys
    """
    if dict_data in (u'', None, {}, [], set()):
        return None
    elif isinstance(dict_data, dict):
        new_dict = {}
        for k, v in dict_data.items():
            if k in ex_key:
                new_dict[k] = v
            else:
                out = stripper(v, ex_key)
                if out is not None:
                    new_dict[k] = out
        return new_dict
    elif isinstance(dict_data, list):
        new_list = []
        for v in dict_data:
            out = stripper(v, ex_key)
            if out is not None:
                new_list.append(out)
        return new_list
    elif isinstance(dict_data, set):
        new_set = set()
        for v in dict_data:
            out = stripper(v, ex_key)
            if out is not None:
                new_set.add(out)
        return new_set
    else:
        return dict_data


class Literal(str):
    pass


def literal_presenter(dumper, data):
    # https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')


yaml.add_representer(Literal, literal_presenter)


def split_type(content: str) -> {}:
    """
    :param content: string(enum:a,b,c)(format:FORMAT) / object(#xxx) / array(#xxx)
    :return: {type, enum, format, $ref, items}
    """
    content = trim(content)
    # Param obj
    if content[0] == '#':
        obj_name = trim(''.join(content[1:]))
        return {
            'type': '',
            'schema': {
                '$ref': f'#/definitions/{obj_name}'
            }
        }

    # Param / Property: object array enum format
    type_ptn = re.compile(r'\((.+?)\)')
    type_name = content.split('(')
    if len(type_name) == 0:
        return None
    type_name = trim(type_name[0])
    obj = {'type': type_name}
    type_ops = type_ptn.findall(content)
    if len(type_ops) == 0:
        return obj

    for op in type_ops:
        op = trim(op)  # (xx)
        if op[0] == '#':  # object / array
            obj_name = trim(''.join(op[1:]))
            if type_name == 'object':
                obj['$ref'] = f'#/definitions/{obj_name}'
            else:
                obj['items'] = {
                    '$ref': f'#/definitions/{obj_name}'
                }
            pass
        else:  # enum / format
            # op -> format:2000-01-01 00:00:00
            ops = op.split(':')
            if len(ops) >= 2:
                op_name = trim(ops[0])
                op_content = trim(':'.join(ops[1:]))
                if op_name == 'enum':
                    obj['enum'] = split_comma(op_content)
                    if type_name == 'integer':
                        obj['enum'] = [int(item) for item in obj['enum']]
                elif op_name == 'format':
                    obj['format'] = op_content
    return obj


def parse_content(content) -> []:
    """
    // @xxx xxx, // @xxx, /* @xxx xxx */, /* @xxx */
    """
    one_line_ptn = re.compile(r'// @(.+)')
    multi_line_ptn = re.compile(r'/\* @(.+?)\*/', re.DOTALL)
    tokens = one_line_ptn.findall(content)
    tokens.extend(multi_line_ptn.findall(content))
    return tokens


def split_kv_helper(tokens: []) -> ([], []):
    """
    helper function: split kv strings to keys and values
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
    parse kv strings to dict
    ['x', 'y z', 'a b', 'a c'] -> {'x': '', 'y': 'z'}
    """
    ks, vs = split_kv_helper(tokens)
    kv = {}
    for idx in range(len(ks)):
        k, v = ks[idx], vs[idx]
        if ks.count(k) == 1:
            kv[k] = v
    return kv


def split_array(tokens: [], array_field: str) -> []:
    """
    parse kv strings to specific array 
    ['a b', 'a c'] -> ['b', 'c']
    """
    ks, vs = split_kv_helper(tokens)
    arr = []
    for idx in range(len(ks)):
        k, v = ks[idx], vs[idx]
        if k == array_field:
            arr.append(trim(v))
    return arr


def field(src: {}, src_field: str, *, required=True) -> str:
    """
    check and get field in dict
    """
    if src_field in src:
        return src[src_field]
    elif not required:
        return ''
    else:
        print(f'Error: don\'t contain required field: {src_field}')
        exit(1)

###


def gen_main(file_path: str) -> {}:
    """
    Generate swagger config from main file
    @Host @BasePath @Title @Description @Version @TermOfService
    @License.Name @License.Url @Contact.Name @Contact.Url @Contact.Email
    @DemoModel @Template @Tag @GlobalSecurity
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

    # @Tag Authorization "Auth-Controller"
    tag_po = []
    tags = split_array(tokens, 'Tag')
    for tag in tags:
        tag_sp = split_bs(tag)
        tag_name = trim(tag_sp[0])
        tag_other = trim(' '.join(tag_sp[1:]))
        tag_other = re.compile(r'"(.*)"').findall(tag_other)
        if len(tag_other) != 0:
            tag_desc = trim(tag_other[0])
            tag_po.append({
                'name': tag_name,
                'description': tag_desc
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

        flags = ['// @Router', '// @Model']
        for flag in flags:
            content_sp = file_content.split(flag)
            if len(content_sp) <= 1:
                continue
            for content in content_sp:
                en = file_content.index(content)
                st = en - len(flag)
                if st < 0:  # first split block in file
                    continue
                if file_content[st:en] != flag:
                    continue
                content = '\n' + flag + content
                # ctrl & model
                if flag == '// @Router':
                    router, method, router_po = gen_ctrl(content, demo_model=demo_model, template=template)
                    if router_po is not None:
                        if router not in paths:
                            paths[router] = {}
                        paths[router][method] = router_po
                elif flag == '// @Model':
                    model_name, model_po = gen_model(content)
                    if model_po is not None:
                        defs[model_name] = model_po

    return paths, defs


def gen_ctrl(content: str, *, demo_model: {}, template: {}) -> (str, str, {}):
    """
    Generate api doc from a route
    @Router @Tag @Accept @Produce @Param 
    @ResponseDesc @ResponseHeader @ResponseModel @ResponseEx
    @Template @Security
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
                'type': ptype,
                'required': preq == 'true',
                'allowEmptyValue': pempty == 'true',
                'description': pdesc,
                'default': pdefault
            }
            if pempty == '*':
                del obj['allowEmptyValue']
            if pdefault != '': 
                if ptype == 'integer' or ptype == 'number':
                    obj['default'] = int(obj['default'])
                elif ptype == 'float' or ptype == 'double':
                    obj['default'] = float(obj['default'])

            # enum -> string(enum:a,b,c)
            # object -> #Result
            ptype_op = split_type(ptype)
            if ptype_op is not None:
                obj.update(ptype_op)
            parameters.append(obj)

        # security
        securities = []
        sec_fields = split_array(tokens, 'Security')
        for sec in sec_fields:
            securities.append({
                sec: []
            })

        # req & resp
        def replace_demo_model(dm_content: str, in_demo_model: {}) -> str:
            """
            replace demoModel through ${} (except \$)
            """
            if in_demo_model is not None:
                dm_content = dm_content.replace('\\$', '$,')
                for dm in re.compile(r'\${(.+?)}').findall(dm_content):
                    if dm not in in_demo_model:
                        continue
                    try:
                        new_dm = json.dumps(in_demo_model[dm])  # <<
                        dm_content = dm_content.replace('${%s}' % dm, new_dm)
                    except:
                        pass
                dm_content = dm_content.replace('$,', '$')
            return dm_content

        def parse_req_resp(desc_anno: str, header_anno: str, model_anno: str, ex_anno: str) -> {}:
            obj = {}
            # Desc
            desc_arr = []
            read_tmpl(desc_arr, desc_anno)
            desc_arr.extend(split_array(tokens, desc_anno))
            for desc in desc_arr:
                rcode, *rmsg = split_bs(desc)
                rmsg = ' '.join(rmsg)
                rmsg = replace_demo_model(rmsg, demo_model)
                if rcode in obj and 'description' in obj[rcode]:
                    rmsg = obj[rcode]['description'] + ', ' + rmsg
                if rcode not in obj:
                    obj[rcode] = {}
                obj[rcode]['description'] = Literal(rmsg)

            # Header
            header_arr = []
            read_tmpl(header_arr, header_anno)
            header_arr.extend(split_array(tokens, header_anno))
            for hdr in header_arr:
                rcode, *rheader = split_bs(hdr)
                rheader = ' '.join(rheader)
                rheader = replace_demo_model(rheader, demo_model)
                rheader = json.loads(rheader)

                if rcode not in obj:
                    obj[rcode] = {}
                if 'headers' not in obj[rcode]:
                    obj[rcode]['headers'] = {}
                for k, v in rheader.items():
                    obj[rcode]['headers'][k] = {
                        'type': 'string',
                        'description': v
                    }

            # Model
            model_arr = []
            read_tmpl(model_arr, model_anno)
            model_arr.extend(split_array(tokens, model_anno))
            for rm in model_arr:
                rcode, *rmodel = split_bs(rm)
                rmodel = trim(' '.join(rmodel))
                obj_ptn = re.compile(r'#(.+)')
                obj_name = obj_ptn.findall(rmodel)
                if len(rmodel) != 0:
                    obj_name = trim(obj_name[0])
                    if rcode not in obj:
                        obj[rcode] = {}
                    obj[rcode]['schema'] = {
                        "$ref": f"#/definitions/{obj_name}"
                    }

            # Body
            example_arr = []
            read_tmpl(example_arr, ex_anno)
            example_arr.extend(split_array(tokens, ex_anno))
            for resp in example_arr:
                rcode, *rjson = split_bs(resp)
                rjson = trim(' '.join(rjson))
                rjson = replace_demo_model(rjson, demo_model)
                rjson = json.loads(rjson)
                rjson = json.dumps(rjson, indent=2, ensure_ascii=False)
                if rcode not in obj:
                    obj[rcode] = {}
                obj[rcode]['examples'] = {
                    'application/json': Literal(rjson)
                }

            return obj

        requests = parse_req_resp('RequestDesc', 'RequestHeader', 'RequestModel', 'RequestEx')
        responses = parse_req_resp('ResponseDesc', 'ResponseHeader', 'ResponseModel', 'ResponseEx')
        for idx, req_resp in enumerate([requests, responses]):
            for r in req_resp.values():
                if 'headers' not in r:
                    r['headers'] = {}
                if 'Content-Type' not in r['headers']:
                    r['headers']['Content-Type'] = {'type': 'string', 'description': ''}
                ct = r['headers']['Content-Type']
                if ct['description'] == '':
                    if idx == 0:
                        ct['description'] = 'application/json'
                    else:
                        ct['description'] = 'application/json; charset=utf-8'

        obj = {
            'operationId': oid,
            'summary': field(kv, 'Summary'),
            'description': field(kv, 'Description', required=False),
            'tags': tags,
            'consumes': accepts,
            'produces': produces,
            'parameters': parameters,
            'security': securities,
            'requests': requests,
            'responses': responses
        }
        return router, method, obj
    except:
        traceback.print_exc()
        return '', '', None


def gen_model(content: str) -> (str, {}):
    """
    Generate definition doc from a model
    @Model @Description @Property
    :return: name, obj
    """
    try:
        tokens = parse_content(content)
        kv = split_dict(tokens)

        # meta
        title = field(kv, 'Model')

        # @Property username string true true "name of user" example
        # prop
        prop_po = {}
        requires = []
        props = split_array(tokens, 'Property')
        for prop in props:
            pname, ptype, preq, pempty, *pother = split_bs(prop)
            pname, ptype = trim(pname), trim(ptype)
            preq, pempty = trim(preq.lower()), trim(pempty.lower())

            pother = trim(' '.join(pother))
            pother_sp = re.compile(r'"(.*)"(.*)').findall(pother)
            pdesc = trim(pother_sp[0][0])
            pexample = trim(pother_sp[0][1])

            if preq == 'true':
                requires.append(pname)
            obj = {
                'description': pdesc,
                'type': ptype,
                'allowEmptyValue': pempty == 'true',
                'example': pexample
            }
            if pempty == '*':
                del obj['allowEmptyValue']
            if pexample != '':
                if ptype == 'integer' or ptype == 'number':
                    obj['example'] = int(obj['example'])
                elif ptype == 'float' or ptype == 'double':
                    obj['example'] = float(obj['example'])

            # enum -> string(enum:a,b,c)
            # nest -> object(#Result)
            ptype_op = split_type(ptype)
            if ptype_op is not None:
                obj.update(ptype_op)
            prop_po[pname] = obj

        obj = {
            'title': title,
            'description': field(kv, 'Description', required=False),
            'type': 'object',  # default array
            'required': requires,
            'properties': prop_po
        }
        return title, obj
    except:
        # traceback.print_exc()
        return '', None

###


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--main', type=str,
                        required=True, help='path of main file containing swagger config')
    parser.add_argument('-s', '--source', type=str,
                        default='.', required=True, help='path of source file')
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
    for root, _, files in os.walk(args.source):
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
    out = stripper(out, ex_key=['security'])
    print(f'> Saving {args.output}...')
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(out, stream=f, encoding='utf-8', allow_unicode=True, sort_keys=False)
    except:
        print(f'Error: failed to save file {args.output}.')
        exit(1)


if __name__ == '__main__':
    main()
