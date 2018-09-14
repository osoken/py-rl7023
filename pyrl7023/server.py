# -*- coding: utf-8 -*-

import os
import time
import json
from logging.config import dictConfig


from flask import Flask, jsonify

from . sensor import RL7023


def gen_app(rb_id, rb_password, config_object=None, logsetting_file=None):
    if logsetting_file is not None:
        with open(logsetting_file, 'r') as fin:
            dictConfig(json.load(fin))
    elif os.getenv('PYRL7023_LOGGER') is not None:
        with open(os.getenv('PYRL7023_LOGGER'), 'r') as fin:
            dictConfig(json.load(fin))
    app = Flask(__name__)
    app.config.from_object('pyrl7023.config')
    if os.getenv('PYRL7023') is not None:
        app.config.from_envvar('PYRL7023')
    if config_object is not None:
        app.config.update(**config_object)

    sensor = RL7023(
        rb_id, rb_password,
        app.config['DEVICE'],
        baudrate=app.config['BAUDRATE'],
        hook=lambda v: app.logger.info('sensor value.', extra=v)
    )

    @app.route('/api/power_consumption')
    def api_co2():
        return jsonify({
            'power_consumption': sensor.power_consumption,
            'timestamp': time.time()
        })

    return app
