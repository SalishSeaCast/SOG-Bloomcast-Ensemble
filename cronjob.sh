# cron script to run SoG-bloomcast
#
# make sure that this file has mode 744
# and that MAILTO is set in crontab

CONDA_BASE_ENV=/home/dlatorne/miniconda3/
CONDA_BLOOMCAST_ENV=/home/dlatorne/conda_envs/bloomcast
RUN_DIR=/data/dlatorne/SOG-projects/SOG-Bloomcast-Ensemble/run
source $CONDA_BASE_ENV/bin/activate $CONDA_BLOOMCAST_ENV && \
    cd $RUN_DIR && \
    $CONDA_BLOOMCAST_ENV/bin/bloomcast ensemble -v config.yaml
