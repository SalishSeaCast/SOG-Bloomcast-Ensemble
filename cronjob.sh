# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744

PYTHON=/ocean/dlatorne/.virtualenvs/SoG-bloomcast/bin/python
cd /ocean/dlatorne/SoG/SOG/SoG-bloomcast && $PYTHON bloomcast/bloomcast.py config.yaml
