#!/bin/bash 
ncores=2
nworkers=100
cluster=pbs
worker_memory=15
dashboard_port=5510
extra_arg='PYTHONPATH=/gpfs/data/schumm-lab/software/conda-env/py38/bin:/apps/software/gcc-6.2.0/bzip2/1.0.6/bin:/apps/compilers/gcc/6.2.0/bin:/apps/software/gcc-6.2.0/miniconda3/4.7.10/condabin:/usr/local/bin:/usr/local/sbin:/usr/lib64/qt-3.3/bin:/opt/moab/bin:/apps/default/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/opt/ibutils/bin:/opt/phoenix/bin:/home/manorathan/bin:home/manorathan/.local/bin'

module load gcc/6.2.0 miniconda3/4.7.10
#source /apps/software/gcc-6.2.0/miniconda3/4.7.10/etc/profile.d/conda.sh
eval "$(conda shell.bash hook)"
conda activate /gpfs/data/schumm-lab/software/conda-env/py38

cd /gpfs/data/schumm-lab/rcg/codebase/py_visualize_accelerometry/hpc_utils

python -u dask_scheduler_config.py --cluster ${cluster} --ncores ${ncores} --nworkers ${nworkers} --worker-memory ${worker_memory} --dashboard-port ${dashboard_port} --cluster-extra-arg ${extra_arg} --localdirectory /scratch/t.phs.mmurugesan --logdirectory /scratch/t.phs.mmurugesan
#python -u dask_scheduler_config.py --cluster-extra-arg ${extra_arg}
