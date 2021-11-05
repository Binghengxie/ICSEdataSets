#!/usr/bin/env python3

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
from os.path import join, dirname, basename, exists
import json
from src.logger import logger
from git import Repo, Git
from src.d2a_label import checkout_back, checkout_to
import subprocess
import threading
import os
import signal
import subprocess
import platform
import multiprocessing


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""
    def __init__(self, files, p):
        super(StoppableThread, self).__init__(group=None)
        self._stop_event = threading.Event()
        self._files = files
        self._p = p

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        while True:
            all_exists = True
            for target_file in self._files:
                if not exists(f"build_sdk-linux-amd64-clang/{target_file}"):
                    all_exists = False
                    break
            if all_exists:
                logger.info("all files exists")
                self._p.kill()
                self._p.terminate()
                os.killpg(self._p.pid, signal.SIGTERM)
                break


def run_cmd(cmd_string, target_files, commit_root, timeout=60):
    print("命令为：" + cmd_string)
    p = subprocess.Popen(cmd_string,
                         stderr=subprocess.STDOUT,
                         stdout=subprocess.PIPE,
                         shell=True,
                         close_fds=True,
                         start_new_session=True)
    # t = StoppableThread(target_files, p)
    t = multiprocessing.Process(target=check_file_exists,
                                args=(
                                    target_files,
                                    p,
                                    commit_root,
                                ))
    t.start()
    format = 'utf-8'
    if platform.system() == "Windows":
        format = 'gbk'

    try:
        (msg, errs) = p.communicate(timeout=timeout)

        ret_code = p.poll()
        if ret_code:
            code = 1
            msg = "[Error]Called Error ： " + str(msg.decode(format))
        else:
            code = 0
            msg = str(msg.decode(format))
    except subprocess.TimeoutExpired:
        # 注意：不能只使用p.kill和p.terminate，无法杀干净所有的子进程，需要使用os.killpg
        p.kill()
        p.terminate()
        os.killpg(p.pid, signal.SIGTERM)

        # 注意：如果开启下面这两行的话，会等到执行完成才报超时错误，但是可以输出执行结果
        # (outs, errs) = p.communicate()
        # print(outs.decode('utf-8'))

        code = 1
        msg = "[ERROR]Timeout Error : Command '" + cmd_string + "' timed out after " + str(
            timeout) + " seconds"
    except Exception as e:
        code = 1
        msg = "[ERROR]Unknown Error : " + str(e)
    # t.stop()
    t.terminate()
    return code, msg


def extract_php():
    project_root = "data/outputs/php-src/"
    prefix = "/home/chengxiao/project/ICSEDataSets/"
    ct = 1
    for commitid in os.listdir(project_root):
        if (ct == 0):
            break
        file_path = join(join(project_root, commitid), "files.json")

        commit_root = join(join(prefix, project_root), commitid)
        if (not exists(file_path)):
            os.system(f"rm -r {commit_root}")
            continue
        with open(file_path, "r") as f:
            files = json.load(f)

        target_files = [
            join(dirname(fl),
                 basename(fl).split(".")[0] + ".o") for fl in files
            if basename(fl).split(".")[1] != "h"
        ]
        repo, err = checkout_to("data/projects/php-src", commitid)
        if (err):
            continue
        if len(target_files) == 0:
            continue

        cur_dir = os.getcwd()
        os.chdir("data/projects/php-src")
        os.system("make clean")
        os.system("./buildconf")
        os.system("CC=wllvm CXX=wllvm++ ./configure")
        run_cmd("CC=wllvm CXX=wllvm++ make -j12", target_files, commit_root,
                300)
        ct -= 1
        # os.system("CC=wllvm CXX=wllvm++ make -j12")

        for target_file in target_files:
            logger.info(f"processing {target_file}")
            if (exists(f"{target_file}")):
                dir_ = join(join(commit_root, "bcs"), dirname(target_file))
                if not exists(dir_):
                    os.makedirs(dir_)
                os.system(f"extract-bc {target_file}")
                logger.info(
                    f"cp {target_file}.bc {join(dir_, basename(target_file))}")
                os.system(
                    f"cp {target_file}.bc {join(dir_, basename(target_file))}")
                os.system(f"rm {target_file}.bc")
        os.system("make clean")
        logger.info(f"complete {commitid}")
        os.chdir(cur_dir)
        checkout_back(repo, "php-src")


def check_file_exists(target_files, p, commit_root):

    while True:
        all_exists = True
        for target_file in target_files:
            if not exists(f"{target_file}"):
                dir_ = join(join(commit_root, "bcs"), dirname(target_file))
                if exists(f"{join(dir_, basename(target_file))}"):
                    continue
                all_exists = False
                break
            else:
                logger.info(f"detect {target_file}")
                os.system(f"extract-bc {target_file}")
                dir_ = join(join(commit_root, "bcs"), dirname(target_file))
                ret = os.system(
                    f"cp {target_file}.bc {join(dir_, basename(target_file))}")
                if ret == 0:
                    logger.info(
                        f"cp {target_file}.bc {join(dir_, basename(target_file))}"
                    )
                os.system(f"rm {target_file}.bc")
                if not exists(f"{join(dir_, basename(target_file))}"):
                    all_exists = False
                    break
        if all_exists:
            logger.info("all exists!")
            p.kill()
            p.terminate()
            os.killpg(p.pid, signal.SIGTERM)
            break


if __name__ == '__main__':
    extract_php()
    # print(subprocess.check_call("extract-bc /home/chengxiao/project/ICSEDataSets/data/projects/php-src/main/streams/cast.c", shell=True))
    # subprocess.call("ls -l", shell=True, cwd="data/projects/avbuild")
    # cur_dir = os.getcwd()
    # os.chdir("data/projects/avbuild")
    # print(os.getcwd())
    # print(os.listdir("./"))
    # os.chdir(cur_dir)
    # print(os.getcwd())
    # print(os.listdir("./"))