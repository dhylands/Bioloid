Bioloid
=======

Python code for working with bioloid devices.

cli.py is a command line program which communicates with devices on the
bioloid bus.

Currently, only serial based interfaces are supported.

In particular, all of the initial testing was done with this device:
http://www.huvrobotics.com/shop/index.php?_a=viewProd&productId=5

To install on a BeagleBone Black:

```bash
wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py

sudo python ez_setup.py
sudo python get-pip.py

sudo pip install virtualenv
sudo pip install virtualenvwrapper

export WORKON_HOME="${HOME}/.venv"
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv bioloid
git clone https://github.com/dhylands/Bioloid
cd Bioloid
pip install -e .
export BIOLOID_PORT=/dev/ttyUSB0
./cli.py
help
```

scan will show detected devices
servo 1 set led on
