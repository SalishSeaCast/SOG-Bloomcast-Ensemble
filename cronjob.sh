# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744

BLOOMCAST=/data/dlatorne/.virtualenvs/bloomcast/bin/bloomcast
cd /data/dlatorne/SOG-projects/SoG-bloomcast/run && $BLOOMCAST config.yaml
