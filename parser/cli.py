#!"python3.exe"

import argparse

from parser.apib import Apib
from parser.swagger import Swagger
from parser.yaml import Yaml

__version__ = '1.0.0'


class CLI:
    version = __version__

    def __init__(self):
        self.args = None
        self.parse_args()
        self.do_yaml = self.args.do_yaml
        self.do_swag = self.args.do_swag
        self.do_apib = self.args.do_apib
        self.run()

    def parse_args(self):
        parser = argparse.ArgumentParser()
        # yaml
        parser.add_argument('-y', '--do_yaml', type=bool, default=True,
                            help='generate yaml file')
        parser.add_argument('-m', '--main', type=str, required=True,
                            help='path of main file containing swagger config')
        parser.add_argument('-d', '--dir', type=str, default='.',
                            required=True, help='path of source directory')
        parser.add_argument('-o', '--yaml_output', type=str, required=True,
                            help='path of output yaml')
        parser.add_argument('-c', '--need_content_type', type=bool, default=False,
                            required=False, help='need Content-Type header or not')
        parser.add_argument('-e', '--ext', type=str, default=[],
                            nargs='*', help='extensions of files wanted to parse')

        # swag
        parser.add_argument('-s', '--do_swag', type=bool, default=False,
                            help='generate swagger2 file')
        parser.add_argument('--swag_output', type=str,
                            required=True, help='path of output html file')

        # apib
        parser.add_argument('-a', '--do_apib', type=bool, default=False,
                            help='generate apib file')
        parser.add_argument('--apib_output', type=str,
                            required=True, help='path of output apib file')

        # parse
        self.args = parser.parse_args()

    def run(self):
        has_yaml = False
        if self.do_yaml:
            has_yaml = True
            Yaml(self.args)

        if self.do_swag:
            if not has_yaml:
                has_yaml = True
                Yaml(self.args)
            Swagger(self.args)

        if self.do_apib:
            if not has_yaml:
                has_yaml = True
                Yaml(self.args)
            Apib(self.args)

        if not has_yaml:
            print('> Error: Not set any action!')


def main():
    CLI()


if __name__ == '__main__':
    main()
