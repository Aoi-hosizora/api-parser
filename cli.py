import argparse
import sys

from apib import Apib
from swagger import Swagger
from main_yaml import Yaml

__version__ = '1.0.0'


class CLI:
    version = __version__

    def __init__(self):
        self.args = None
        self.parse_args()
        self.do_yaml = self.args.do_yaml
        self.do_swag = self.args.do_swag
        self.do_apib = self.args.do_apib

        self.has_yaml = False
        self.run()

    def parse_args(self):
        parser = argparse.ArgumentParser()
        # yaml
        parser.add_argument('-y', '--do_yaml', action='store_true', default=True,
                            help='generate yaml file')
        parser.add_argument('-m', '--main', type=str, required=True,
                            help='path of main file containing swagger config')
        parser.add_argument('-d', '--dir', type=str, default='.',
                            help='path of source directory')
        parser.add_argument('-o', '--yaml_output', type=str, required=True,
                            help='path of output yaml')
        parser.add_argument('-c', '--need_content_type', action='store_true',
                            help='need Content-Type header or not')
        parser.add_argument('-e', '--ext', type=str, default=[], nargs='*',
                            help='extensions of files wanted to parse')

        # swag
        parser.add_argument('-s', '--do_swag', action='store_true', default=False,
                            help='generate swagger2 file')
        parser.add_argument('--swag_output', type=str,
                            help='path of output html file')

        # apib
        parser.add_argument('-a', '--do_apib', action='store_true', default=False,
                            help='generate apib file')
        parser.add_argument('--apib_output', type=str,
                            help='path of output apib file')

        # parse
        self.args = parser.parse_args()

    def run_yaml(self):
        self.has_yaml = True
        print('\n> Do generate yaml...')
        if not self.args.yaml_output:
            print('> Error: --yaml_output is empty')
            sys.exit(1)
        Yaml(self.args)

    def run_swag(self):
        if not self.has_yaml:
            self.run_yaml()
        print('\n> Do generate swagger (*.html)...')
        if not self.args.swag_output:
            print('> Error: --swag_output is empty')
            sys.exit(1)
        Swagger(self.args)

    def run_apib(self):
        if not self.has_yaml:
            self.run_yaml()
        print('\n> Do generate apib (*.apib)...')
        if not self.args.apib_output:
            print('> Error: --apib_output is empty')
            sys.exit(1)
        Apib(self.args)

    def run(self):
        if self.do_yaml:
            self.run_yaml()
        if self.do_swag:
            self.run_swag()
        if self.do_apib:
            self.run_apib()

        if not self.has_yaml:
            print('> Error: Not set any action!')


def main():
    CLI()


if __name__ == '__main__':
    main()
