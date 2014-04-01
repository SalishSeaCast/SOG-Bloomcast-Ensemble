# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744
# and that MAILTO is set in crontab

VENV=/data/dlatorne/.virtualenvs/bloomcast-ensemble
RUN_DIR=/data/dlatorne/SOG-projects/SoG-bloomcast-ensemble/run
. $VENV/bin/activate && cd $RUN_DIR && $VENV/bin/bloomcast ensemble -v config.yaml
