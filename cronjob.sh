# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744
# and that MAILTO is set in crontab

RUN_DIR=/data/dlatorne/SOG-projects/SOG-Bloomcast-Ensemble/run
cd $RUN_DIR && \
  pixi run bloomcast ensemble -v config.yaml --debug
