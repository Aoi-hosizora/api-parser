import json
import sys

import yaml

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Swagger UI</title>
    <link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700|Source+Code+Pro:300,600|Titillium+Web:400,600,700" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/swagger-ui.css" rel="stylesheet">
    <style>
    html {
        box-sizing: border-box;
        overflow: -moz-scrollbars-vertical;
        overflow-y: scroll;
    }
    *, *:before, *:after {
        box-sizing: inherit;
    }
    body {
        margin:0;
        background: #fafafa;
    }
    div#swagger-ui .markdown pre code.language-json, /* markdown json block */
    div#swagger-ui div.highlight-code pre.microlight, /* swagger example */
    div#swagger-ui span.model, /* example model */
    div#swagger-ui table.model, /* example model */
    div#swagger-ui table.headers td.header-col { /* header */
        font-family: consolas;
        font-weight: 600;
        font-size: 14px;
        font-style: italic;
    }
    div#swagger-ui div.highlight-code pre.microlight { /* swagger example value */
        background: rgba(0, 0, 0, 0.05);
    }
    div#swagger-ui div.highlight-code pre.microlight span { /* swagger example value */
        color: #9012fe!important;
    }
    div#swagger-ui div.model-box { /* swagger example json display */
        display: block;
    }
    div#swagger-ui textarea {
        font-family: consolas;
        font-size: 14px;
    }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.20.0/swagger-ui-bundle.js"> </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.20.0/swagger-ui-standalone-preset.js"> </script>
    <script>
    window.onload = function() {
        var spec = %s;
        window.ui = SwaggerUIBundle({
            spec: spec,
            dom_id: '#swagger-ui',
            validatorUrl: null,
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout"
        });
    }
    </script>
</body>
</html>
"""


def run(yaml_name, swag_output):
    # noinspection PyBroadException
    try:
        print(f'> Reading {yaml_name}...')
        content = open(yaml_name, 'r', encoding='utf-8').read()
    except:
        print(f'Error: failed to open file {yaml_name}.')
        sys.exit(1)

    spec = yaml.load(content, Loader=yaml.FullLoader)
    html = TEMPLATE % json.dumps(spec)

    # noinspection PyBroadException
    try:
        print(f'> Saving {swag_output}...')
        with open(swag_output, 'w', encoding='utf-8') as f:
            f.write(html)
    except:
        print(f'Error: failed to save file {swag_output}.')
        sys.exit(1)


class Swagger:

    def __init__(self, args):
        run(args.yaml_output, args.swag_output)
