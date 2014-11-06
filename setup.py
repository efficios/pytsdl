#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (c) 2014 Philippe Proulx <philippe.proulx@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import os
import sys
import subprocess
from setuptools import setup


# make sure we run Python 3+ here
v = sys.version_info
if v.major < 3:
    sys.stderr.write('Sorry, pytsdl needs Python 3\n')
    sys.exit(1)


def _which(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)

    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)

            if is_exe(exe_file):
                return exe_file

    return None


# Because of a tarball wrongly distributed by PyPI, we cannot use
# install_requires here. Running pip directly works, however.
if len(sys.argv) > 1 and sys.argv[1] in ['install', 'develop']:
    pip_exe = _which('pip3')

    if pip_exe is None:
        pip_exe = _which('pip')

    if pip_exe is None:
        print('Error: please install pip for Python 3 (pip3 on some distros)',
              file=sys.stderr)
        sys.exit(1)

    try:
        if subprocess.call([pip_exe, 'install', 'pyPEG2', '--upgrade']) != 0:
            raise RuntimeError()
    except:
        print('Error: cannot run "{} install pyPEG2 --upgrade"'.format(pip_exe),
              file=sys.stderr)
        sys.exit(1)


packages = [
    'pytsdl',
]


setup(name='pytsdl',
      version=0.2,
      description='TSDL parser implemented entirely in Python 3',
      author='Philippe Proulx',
      author_email='eeppeliteloop@gmail.com',
      url='https://github.com/eepp/pytsdl',
      packages=packages)
