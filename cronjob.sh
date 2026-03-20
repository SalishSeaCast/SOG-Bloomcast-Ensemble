# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744
# and that MAILTO is set in crontab

PROJECT_DIR=/data/dlatorne/SOG-projects/SOG-Bloomcast-Ensemble
cd $PROJECT_DIR/run && \
  /home/dlatorne/.pixi/bin/pixi run -m $PROJECT_DIR bloomcast ensemble -v config.yaml --debug
