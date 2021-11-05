#!/usr/bin/env python3


import sys
import os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import json

from git import Repo, Git
from os.path import exists, dirname
import subprocess
from src.logger import logger
from src.d2a_label import is_cpp


def checkto_main(r, project):
    backname = 'master'
    if project == 'httpd':
        backname = 'trunk'
    elif project == 'libgit2':
        backname = 'main'
    print('checkout workspace to current')
    try:
        r.execute('git reset ' + backname + ' --hard', shell=True)
    except Exception as e:
        logger.error(e)
    logger.info('checkout end !')
    
    
def checkout_to(project, repo_dir, commit_id):

    logger.info(f'checkout workspace to {commit_id}')
    r = Git(repo_dir)
    checkto_main(r, project)
    try:
        r.execute('git checkout ' + commit_id + ' -f', shell=True)
    except Exception as e:
        # r.execute('git branch -D ' + commit_id, shell=True)
        logger.error(e)
    logger.info('checkout end !')
    r.update_environment()
    return r

def check_finish(project_name, commit_id):
    """
    commit id finished configure return True
    """
    done_idxes_path = f"data/d2a/{project_name}/done_configure.txt"
    if not exists(done_idxes_path):
        os.system(f"touch {done_idxes_path}")
    with open(done_idxes_path, "a+") as f:
        done_idxes = set(f.read().split(","))
        if commit_id in done_idxes:
            logger.info(f"skip {commit_id}")
            return True
        f.write(commit_id + ",")
        f.close()
    return False

def configure(project, repo_dir, commit_id):
    if project == "nginx":
        r = checkout_to(project, repo_dir, commit_id)
        if os.path.isfile("{}/auto/cc/clang".format(repo_dir)):
            with open("{}/auto/cc/clang".format(repo_dir), "a+") as f1:
                f1.write('CFLAGS="$CFLAGS -S -emit-llvm"')
                f1.close()
        subprocess.call(["bash","nginx.sh"], cwd = "data/projects")
        logger.info(f"configure done for {project}/{commit_id}")
        return r
    
def cp_bc(proj_name:str, repo:str, single_file:str, target, commit_id):
    """
    :param repo: repo path search_parent_directories=True
    :param single_file: single file path
    target: stored data path.
    :return: -
    """
    # subprocess way to double check
    process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], cwd = repo, shell=False, stdout=subprocess.PIPE)
    git_head_hash = process.communicate()[0].strip().decode('UTF-8')

    if (git_head_hash != commit_id):
        logger.info(f"not match {commit_id} and skip")
        return
    else:
        # src/core/ngx_file.o
        obj = single_file.split(".")[0] + ".o"
        if proj_name == "nginx":
            file = f"{repo}/objs/{obj}"
            subprocess.call(["mkdir", "-p", f"{target}/{dirname(obj)}"])
            subprocess.call(["cp", f"{file}", f"{target}/{dirname(obj)}"])
            logger.info(f"copy done {file}")
            
def pipeline(project):
    output_path = f"data/outputs/{project}"
    repo = f"data/projects/{project}"
    for commit_id in os.listdir(output_path):
        #annotate for finished commit_id not run again in current project
        if not check_finish(project, commit_id):
            r = configure(project, repo, commit_id)
            logger.info(f"current commit id is {commit_id} \n" )
            if exists(f"{output_path}/{commit_id}/files.json"):
                with open(f"{output_path}/{commit_id}/files.json", 'r') as f:
                    file_ls = eval(f.read())
                    print(f"current commit id is {commit_id} \n")
                    for single_file in file_ls:
                        #single_file from src: src/core/ngx_file.c
                        if is_cpp(single_file):
                            cp_bc(project, repo, single_file, f"{output_path}/{commit_id}/bcs", commit_id)
                        else:
                            continue
        else:
            continue
if __name__ == '__main__':
    pipeline(sys.argv[1])