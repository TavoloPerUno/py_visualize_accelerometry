from dask.distributed import Client, wait
import os
import argparse
from datetime import datetime
import sys
import logging
import time
sys.path.append('../')
from hrsa_utils import dataframe_utils, recipes
from dask_jobqueue import SLURMCluster
from dask_jobqueue import PBSCluster
logname = 'dask_scheduler'
logger = logging.getLogger(logname)

def get_client_ip(location, ncores, memory_in_gb, dashboard_port,
                log_directory='/scratch/t.phs.mmurugesan/dask/log',
                local_directory='/scratch/t.phs.mmurugesan/dask/dask-tmp',
                nworkers=None,
                logger=None,
                extra_arg="",
                walltime="36:00:00"
                ):
    cluster = SLURMCluster(queue='broadwl',
                               project='pi-guiming',
                               cores=ncores,
                               log_directory=log_directory,
                               memory="{0} GB".format(str(memory_in_gb)),
                               dashboard_address=":{0}".format(str(dashboard_port)),
                               walltime=walltime,
                           env_extra=extra_arg.split(",")
                           ) if (location == 'slurm') else \
            PBSCluster(cores=ncores,
                             interface='ib0',
                             walltime=walltime,
                             memory="{0} GB".format(str(memory_in_gb)),
                             log_directory=log_directory,
                             local_directory=local_directory,
                             resource_spec='nodes=1:ppn=1',
                             dashboard_address=":{0}".format(str(dashboard_port)),
                             job_extra=["-l mem={0}gb".format(str(memory_in_gb))],
                       env_extra=extra_arg.split(",")
                             )
    logger.info(cluster.job_script())
    if nworkers is not None:
        cluster.scale(jobs=nworkers)
    client = Client(cluster)
    logger.info("Starting dask scheduler at {0}".format(client.scheduler_info()['address']))
    logger.info("Dashboard at {0}".format(client.scheduler_info()['services']['dashboard']))
    if nworkers is not None:
        wait_for_workers = 1
        while (wait_for_workers == 1):
            if bool(client.scheduler_info()['workers']):
                wait_for_workers = 0
                logger.info("Workers available")
    return client.scheduler_info()['address']

def main(argv):
    parser = argparse.ArgumentParser(description='Export data for Diabetes manuscript')
    # Required positional argument
    parser.add_argument('--cluster', type=str, default='stats', choices=['stats', 'local', 'pbs', 'slurm'])
    parser.add_argument('--ncores', type=int, default='3')
    parser.add_argument('--nworkers', type=int, default='12')
    parser.add_argument('--worker-memory', type=int, default='160')
    parser.add_argument('--dashboard-port', type=int, default='9510')
    parser.add_argument('--cluster-extra-arg', type=str, default="")
    parser.add_argument('--walltime', type=str, default="120:00:00")
    parser.add_argument('--logdirectory', type=str, default="/scratch/t.phs.mmurugesan/dask/log")
    parser.add_argument('--localdirectory', type=str, default="/scratch/t.phs.mmurugesan/dask/log")
    parser.add_argument('--log-level', type=str, default='DEBUG',
                        choices=['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='loglevels')
    global logger
    global logname
    args = parser.parse_args()
    logfilename = os.path.join('..', 'logs', 'dask_distributed {:%Y-%m-%d %H:%M:%S}.log'.format(datetime.now()))
    logger = recipes.setup_custom_logger(logname, logfilename, args.log_level)
    client_ip = get_client_ip(args.cluster, args.ncores, args.worker_memory, args.dashboard_port, args.logdirectory,
                              args.localdirectory, nworkers=args.nworkers, logger=logger,
                              extra_arg=args.cluster_extra_arg, walltime=args.walltime)
    time.sleep(259200)



if __name__ == '__main__':
    main(sys.argv[1:])