#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
#sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.dirname(__file__))
from admin.app import app

if __name__ == "__main__":
    app.run(debug=True)