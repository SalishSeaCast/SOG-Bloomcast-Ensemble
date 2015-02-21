# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744
# and that MAILTO is set in crontab

CONDA_ENV=/home/dlatorne/anaconda/envs/bloomcast
RUN_DIR=/data/dlatorne/SOG-projects/SoG-bloomcast-ensemble/run
source $CONDA_ENV/bin/activate bloomcast && cd $RUN_DIR && $CONDA_ENV/bin/bloomcast ensemble -v config.yaml
