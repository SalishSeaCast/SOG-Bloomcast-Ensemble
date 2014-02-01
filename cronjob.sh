# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744
# and that MAILTO is set in crontab

VENV=/data/dlatorne/.virtualenvs/bloomcast
RUN_DIR=/data/dlatorne/SOG-projects/SoG-bloomcast/run
. $VENV/bin/activate && cd $RUN_DIR && $VENV/bin/bloomcast config.yaml
