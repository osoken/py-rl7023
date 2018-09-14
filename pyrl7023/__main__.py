# -*- coding: utf-8 -*-

import os
from argparse import ArgumentParser

from . server import gen_app

parser = ArgumentParser(description='run RL7023 sensor server')
parser.add_argument('--rb_id', default=os.getenv('PYRL7023_RB_ID'))
parser.add_argument('--rb_password', default=os.getenv('PYRL7023_RB_PASSWORD'))

args = parser.parse_args()

app = gen_app(args.rb_id, args.rb_password)

app.run(host=app.config['HOST'], port=app.config['PORT'])
