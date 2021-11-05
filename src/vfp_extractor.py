import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from os.path import exists, join, dirname, basename
from os import listdir, stat
import json
from src.logger import logger
from typing import Dict, List
from sklearn.model_selection import train_test_split
from src.d2a_label import checkout_to, checkout_back


def encode_apis(apis: List[str]):
    with open("/home/chengxiao/project/VFPExtractor/data/API.txt", "r") as f:
        all_apis = f.read().split(",")
        all_apis_s = set(all_apis)
    outstr = ""
    for api in apis:
        if api in all_apis_s:
            outstr += chr(all_apis.index(api))
        else:
            raise ValueError(f"{api} not found!")
    return outstr


def encode_types(types: List[int]):
    outstr = ""
    for t in types:
        outstr += chr(t)
    return outstr


def write_source_code(file_path: str, commit_root: str, project_root: str):
    dir_name = dirname(file_path)
    if not exists(join(f"{commit_root}/files", dir_name)):
        os.makedirs(join(f"{commit_root}/files", dir_name))
    if not exists(join(f"{commit_root}/files", file_path)):
        tgt = join(f"{commit_root}/files", file_path)
        os.system(f"cp {join(project_root, file_path)} {tgt}")


def cp_missed_files(project: str):
    project_root = f"data/outputs/{project}"
    commitids = listdir(project_root)
    prefix_p = "/home/chengxiao/project/ICSEDataSets"

    for commitid in commitids:
        visited_method = set()
        commit_root = join(project_root, commitid)
        logger.info(f"Processing {commit_root}..")
        label_path = join(commit_root, "label.json")
        if (exists(label_path)):
            with open(label_path, "r") as f:
                labels = json.load(f)
        else:
            logger.info(f"no label for {commit_root}")
            continue

        for i, label in enumerate(labels):

            if label["source"] in ["auto1", "after0"]:
                label_funcs = label["label_funcs"]
                for j, func in enumerate(label_funcs):
                    funcid = func["file_path"] + "|" + func["method"][
                        0] + "|" + str(func["method"][1]) + "|" + str(
                            func["method"][2])
                    if (funcid in visited_method):
                        continue
                    visited_method.add(funcid)
                    if "flows" in func:
                        # file_path = join(
                        #     join(join(prefix_p, commit_root), "files"),
                        #     func["file_path"])

                        # graph_path = join(
                        #     join(join(prefix_p, commit_root), "graphs"),
                        #     func["file_path"])
                        # if not exists(join(graph_path, "nodes.csv")):
                        #     logger.info("no graph path, skip")
                        #     continue
                        for flow in func["flows"]:
                            file_paths = flow["files"]
                            for file_path_idx, file_path in enumerate(
                                    file_paths):
                                abs_file_path = join(
                                    join(join(prefix_p, commit_root), "files"),
                                    file_path)
                                if (not exists(abs_file_path)):
                                    repo = checkout_to(project_root, commitid)
                                    write_source_code(file_path, commit_root,
                                                      project_root)
                                    checkout_back(repo, project)


def reduce_flow_file_size(v_flows):
    for idx, v_flow in enumerate(v_flows):
        files = v_flow["files"]
        statements = v_flow["statements"]
        old_to_new = dict()
        fil_set = set()
        for st in statements:
            fil_set.add(int(st.split(",")[0]))
        v_flows[idx]["files"] = list()
        for j, fil in enumerate(list(fil_set)):
            old_to_new[fil] = j
            v_flows[idx]["files"].append(files[j])
        v_flows[idx]["statements"] = list()
        for st in statements:
            spts = st.split(",")
            v_flows[idx]["statements"].append(
                str(old_to_new[int(spts[0])]) + "," + spts[1])
    return v_flows


def extract_d2a_method_vfs(project: str):
    # path to value flow extractor binary
    vfex = "/home/chengxiao/project/VFPExtractor/Debug-build/bin/vfex"
    # tmp path to output value flows for vfex
    vf_outtmp = "/home/chengxiao/project/ICSEDataSets/data/vfps_tmp/"
    assert exists(vfex), f"wrong path for vfex: {vfex}"
    project_root = f"data/outputs/{project}"
    commitids = listdir(project_root)
    total = 0
    for commitid in commitids:
        commit_root = join(project_root, commitid)
        logger.info(f"Processing {commit_root}..")
        label_path = join(commit_root, "label.json")
        if (exists(label_path)):
            with open(label_path, "r") as f:
                labels = json.load(f)
        else:
            logger.info(f"no label for {commit_root}")
            continue
        funcid_to_vflows = dict()
        for i, label in enumerate(labels):
            # if label["source"] in ["auto1", "after0", "auto0"]:
            label_funcs = label["label_funcs"]
            for j, func in enumerate(label_funcs):
                # if "flows" in func and len(func["flows"]) != 0:
                #     total += 1
                #     logger.info("have been processed, skip!")
                #     continue

                # skip .h file
                if (func["file_path"].endswith(".h")):
                    labels[i]["label_funcs"][j]["flows"] = []
                    labels[i]["label_funcs"][j]["phase"] = "start"
                    continue
                funcid = func["file_path"] + "|" + func["method"][
                    0] + "|" + str(func["method"][1]) + "|" + str(
                        func["method"][2])
                if funcid in funcid_to_vflows:
                    labels[i]["label_funcs"][j]["flows"] = funcid_to_vflows[
                        funcid]
                    labels[i]["label_funcs"][j]["phase"] = "raw"
                    continue
                dir_ = dirname(func["file_path"])
                base_ = basename(func["file_path"])
                source_file_path = join(join(commit_root, "files"),
                                        func["file_path"])
                file_path = join(join(commit_root, "bcs"),
                                 join(dir_,
                                      base_.split(".")[0] + ".o"))
                method_name = func["method"][0]
                if (not exists(file_path)):
                    labels[i]["label_funcs"][j]["flows"] = []
                    labels[i]["label_funcs"][j]["phase"] = "start"
                    continue
                os.system(f"rm {vf_outtmp}output.tmp")
                logger.info(
                        f"{vfex} {file_path} --method-name {method_name} --file-name {func['file_path']} --mode 1 --output {vf_outtmp}"
                    )
                ret = os.system(
                    f"{vfex} {file_path} --method-name {method_name} --file-name {func['file_path']} --mode 1 --output {vf_outtmp}"
                )
                if (ret != 0 or (not exists(join(vf_outtmp, "output.tmp")))):
                    # vfextraction has errors, we skip this function
                    logger.error(
                        f"{vfex} {file_path} --method-name {method_name} --file-name {func['file_path']} --mode 1 --output {vf_outtmp}"
                    )
                    logger.error(
                        f"{source_file_path} {file_path} --method-name {method_name} --mode 1"
                    )
                    labels[i]["label_funcs"][j]["flows"] = []
                    labels[i]["label_funcs"][j]["phase"] = "start"
                    continue
                with open(join(vf_outtmp, "output.tmp"), "r") as f:
                    flows = f.readlines()
                # ct = 5
                ct = 4
                vf_dict: Dict[str, List[Dict[str, Dict]]] = dict()
                for flow in flows:
                    # if ct == 5:
                    #     vf_tmp = dict()
                    #     vf_tmp["files"] = flow.strip().split("|")[:-1]
                    if ct == 4:
                        vf_tmp = dict()
                        st_k = flow.strip()
                        vf_tmp["statements"] = [
                            st for st in st_k.split("|")[:-1]
                        ]
                    elif ct == 3:
                        vf_tmp["apis"] = flow.strip().split("|")[:-1]
                    elif ct == 2:
                        vf_tmp["types"] = [
                            int(st) for st in flow.strip().split("|")[:-1]
                        ]
                    elif ct == 1:
                        vf_tmp["nodekinds"] = [
                            int(st) for st in flow.strip().split("|")[:-1]
                        ]
                    elif ct == 0:
                        vf_tmp["nodeids"] = [
                            int(st) for st in flow.strip().split("|")[:-1]
                        ]
                        if st_k not in vf_dict:
                            vf_dict[st_k] = dict()
                        vf_dict[st_k][len(vf_tmp["apis"]) +
                                      len(vf_tmp["types"])] = vf_tmp
                        # ct = 6
                        ct = 5
                    else:
                        raise ValueError("not valid count!")
                    ct -= 1
                v_flows = list()
                for st_k in vf_dict:
                    vfps = vf_dict[st_k]
                    sorted_vfps = sorted(vfps)
                    if (len(sorted_vfps) > 0):
                        v_flows.append(vfps[sorted_vfps[-1]])
                # v_flows = reduce_flow_file_size(v_flows)
                labels[i]["label_funcs"][j]["flows"] = v_flows
                funcid_to_vflows[funcid] = v_flows
                labels[i]["label_funcs"][j]["phase"] = "raw"
                total += 1
        with open(label_path, "w") as f:
            json.dump(labels, f)
    logger.info(f"total {total} functions")
    # cp_missed_files("nginx")


def extract_d2a_slice_vfs(project: str):
    # path to value flow extractor binary
    vfex = "/home/chengxiao/project/VFPExtractor/Debug-build/bin/vfex"
    # tmp path to output value flows for vfex
    vf_outtmp = "/home/chengxiao/project/ICSEDataSets/data/vfps_tmp/"
    prefix_p = "/home/chengxiao/project/ICSEDataSets"
    assert exists(vfex), f"wrong path for vfex: {vfex}"
    project_root = f"data/outputs/{project}"
    commitids = listdir(project_root)
    total = 0
    for commitid in commitids:
        commit_root = join(project_root, commitid)
        logger.info(f"Processing {commit_root}..")
        label_path = join(commit_root, "label.json")
        if (exists(label_path)):
            with open(label_path, "r") as f:
                labels = json.load(f)
        else:
            logger.info(f"no label for {commit_root}")
            continue
        file_to_slices = dict()
        for i, label in enumerate(labels):
            if label["source"] == "after0":
                continue
            # skip .h file
            if (label["file_path"].endswith(".h")):
                continue
            dir_ = dirname(label["file_path"])
            base_ = basename(label["file_path"])
            source_file_path = join(join(commit_root, "files"),
                                    label["file_path"])
            file_path = join(join(commit_root, "bcs"),
                             join(dir_,
                                  base_.split(".")[0] + ".o"))
            if (not exists(file_path)):
                continue
            out_files = join(vf_outtmp, "files.tmp")
            os.system(f"rm {vf_outtmp}outs/*")
            os.system(f"rm {out_files}")
            ret = os.system(
                f"{vfex} {file_path} --mode 2 --output {vf_outtmp}")

            if (ret != 0 or (not exists(out_files))):
                # vfextraction has errors, we skip this function
                logger.error(
                    f"{vfex} {file_path} --mode 2 --output {vf_outtmp}")
                logger.error(f"{source_file_path} {file_path}")
                continue
            with open(out_files, "r") as f:
                file_paths = f.read().strip().split("|")[:-1]
            # copy missed files
            for file_p in file_paths:
                abs_file_path = join(
                    join(join(prefix_p, commit_root), "files"), file_p)
                if (not exists(abs_file_path)):
                    repo = checkout_to(project_root, commitid)
                    write_source_code(file_path, commit_root, project_root)
                    checkout_back(repo, project)
            if label["source"] == "auto1":
                if (label["file_path"] in file_to_slices):
                    slices = file_to_slices[label["file_path"]]
                    # extract statements label
                    vul_statements = set()
                    for trace in label["trace"]:
                        if (trace["file_path"] in slices["files"]):
                            vul_statements.add(
                                str(slices["files"].index(trace["file_path"]))
                                + "," + trace["loc"].split(":")[0])

                    for idx, s in enumerate(slices["slices"]):
                        flaws = set()
                        for v_flow in s["flows"]:

                            flaws = flaws.union(
                                vul_statements.intersection(
                                    v_flow["statements"]))
                        if (len(flaws) != 0):
                            slices["slices"][idx]["label"] = 1
                            slices["slices"][idx]["flaws"] = list(flaws)
                        else:
                            slices["slices"][idx]["label"] = 0
                            slices["slices"][idx]["flaws"] = []
                    labels[i]["slices"] = slices
                    continue

                # extract statements label
                vul_statements = set()
                for trace in label["trace"]:
                    if (trace["file_path"] in file_paths):
                        vul_statements.add(
                            str(file_paths.index(trace["file_path"])) + "," +
                            trace["loc"].split(":")[0])
                outs_dir = join(vf_outtmp, "outs")
                # for each slice
                slices = dict()
                slices["files"] = file_paths
                slices["slices"] = list()
                for slice_f in listdir(outs_dir):
                    with open(join(outs_dir, slice_f), "r") as f:
                        flows = f.readlines()
                    ct = 4
                    vf_dict: Dict[str, List[Dict[str, Dict]]] = dict()
                    for flow in flows:
                        # if ct == 5:
                        #     vf_tmp = dict()
                        #     vf_tmp["files"] = flow.strip().split("|")[:-1]
                        if ct == 4:
                            vf_tmp = dict()
                            st_k = flow.strip()
                            vf_tmp["statements"] = [
                                st for st in st_k.split("|")[:-1]
                            ]
                        elif ct == 3:
                            vf_tmp["apis"] = flow.strip().split("|")[:-1]
                        elif ct == 2:
                            vf_tmp["types"] = [
                                int(st) for st in flow.strip().split("|")[:-1]
                            ]
                        elif ct == 1:
                            vf_tmp["nodekinds"] = [
                                int(st) for st in flow.strip().split("|")[:-1]
                            ]
                        elif ct == 0:
                            vf_tmp["nodeids"] = [
                                int(st) for st in flow.strip().split("|")[:-1]
                            ]
                            if st_k not in vf_dict:
                                vf_dict[st_k] = dict()
                            vf_dict[st_k][len(vf_tmp["apis"]) +
                                          len(vf_tmp["types"])] = vf_tmp
                            # ct = 6
                            ct = 5
                        else:
                            raise ValueError("not valid count!")
                        ct -= 1
                    v_flows = list()
                    for st_k in vf_dict:
                        vfps = vf_dict[st_k]
                        sorted_vfps = sorted(vfps)
                        if (len(sorted_vfps) > 0):
                            v_flows.append(vfps[sorted_vfps[-1]])
                    slice_item = dict()
                    slice_item["flows"] = v_flows
                    flaws = set()
                    for v_flow in v_flows:

                        flaws = flaws.union(
                            vul_statements.intersection(v_flow["statements"]))
                    if (len(flaws) != 0):
                        slice_item["label"] = 1
                        slice_item["flaws"] = list(flaws)
                    else:
                        slice_item["label"] = 0
                        slice_item["flaws"] = []
                    slices["slices"].append(slice_item)

                    total += 1
                labels[i]["slices"] = slices
                file_to_slices[label["file_path"]] = slices
            elif label["source"] == "auto0":
                if (label["file_path"] in file_to_slices):
                    slices = file_to_slices[label["file_path"]]
                    labels[i]["slices"] = slices
                    continue
                # for each slice
                slices = dict()
                slices["files"] = file_paths
                slices["slices"] = list()
                for slice_f in listdir(outs_dir):
                    with open(join(outs_dir, slice_f), "r") as f:
                        flows = f.readlines()
                    ct = 4
                    vf_dict: Dict[str, List[Dict[str, Dict]]] = dict()
                    for flow in flows:
                        # if ct == 5:
                        #     vf_tmp = dict()
                        #     vf_tmp["files"] = flow.strip().split("|")[:-1]
                        if ct == 4:
                            vf_tmp = dict()
                            st_k = flow.strip()
                            vf_tmp["statements"] = [
                                st for st in st_k.split("|")[:-1]
                            ]
                        elif ct == 3:
                            vf_tmp["apis"] = flow.strip().split("|")[:-1]
                        elif ct == 2:
                            vf_tmp["types"] = [
                                int(st) for st in flow.strip().split("|")[:-1]
                            ]
                        elif ct == 1:
                            vf_tmp["nodekinds"] = [
                                int(st) for st in flow.strip().split("|")[:-1]
                            ]
                        elif ct == 0:
                            vf_tmp["nodeids"] = [
                                int(st) for st in flow.strip().split("|")[:-1]
                            ]
                            if st_k not in vf_dict:
                                vf_dict[st_k] = dict()
                            vf_dict[st_k][len(vf_tmp["apis"]) +
                                          len(vf_tmp["types"])] = vf_tmp
                            # ct = 6
                            ct = 5
                        else:
                            raise ValueError("not valid count!")
                        ct -= 1
                    v_flows = list()
                    for st_k in vf_dict:
                        vfps = vf_dict[st_k]
                        sorted_vfps = sorted(vfps)
                        if (len(sorted_vfps) > 0):
                            v_flows.append(vfps[sorted_vfps[-1]])
                    slice_item = dict()
                    slice_item["flows"] = v_flows
                    slice_item["label"] = 0
                    slice_item["flaws"] = []
                    slices["slices"].append(slice_item)

                    total += 1
                labels[i]["slices"] = slices
                file_to_slices[label["file_path"]] = slices
        with open(label_path, "w") as f:
            json.dump(labels, f)
    logger.info(f"total {total} slices")
    # cp_missed_files("nginx")


def build_d2a_vfs_cl(project: str):
    project_root = f"data/outputs/{project}"
    commitids = listdir(project_root)
    out_path = f"/home/chengxiao/project/ICSE22/data/cl_pretraining/d2a/{project}.json"
    prefix_p = "/home/chengxiao/project/ICSEDataSets"

    vfs_all = list()
    for commitid in commitids:
        visited_method = set()
        commit_root = join(project_root, commitid)
        logger.info(f"Processing {commit_root}..")
        label_path = join(commit_root, "label.json")
        if (exists(label_path)):
            with open(label_path, "r") as f:
                labels = json.load(f)
        else:
            logger.info(f"no label for {commit_root}")
            continue

        for i, label in enumerate(labels):

            # if label["source"] in ["auto1", "after0", "auto0"]:
            label_funcs = label["label_funcs"]
            for j, func in enumerate(label_funcs):
                funcid = func["file_path"] + "|" + func["method"][
                    0] + "|" + str(func["method"][1]) + "|" + str(
                        func["method"][2])
                if (funcid in visited_method):
                    continue
                visited_method.add(funcid)
                if "flows" in func:
                    file_path = join(
                        join(join(prefix_p, commit_root), "files"),
                        func["file_path"])

                    graph_path = join(
                        join(join(prefix_p, commit_root), "graphs"),
                        func["file_path"])
                    if not exists(join(graph_path, "nodes.csv")):
                        logger.info("no graph path, skip")
                        continue
                    for flow in func["flows"]:
                        flow_item = dict()
                        flow_item["files"] = [file_path]
                        flow_item["graph_paths"] = [graph_path]

                        with open(file_path,
                                  "r",
                                  encoding="utf-8",
                                  errors="ignore") as f:
                            file_content = f.readlines()
                        statements = list()

                        for st in flow["statements"]:
                            ln = int(st.split(",")[1])
                            if ln - 1 == len(file_content):
                                ln -= 1
                            if (ln - 1 >= len(file_content)):
                                logger.error(
                                    f"{file_path} {str(func['method'])} {str(flow['statements'])} "
                                )
                                continue
                            if (file_content[ln - 1].strip() != ""):
                                statements.append("0," + str(ln))
                        if (len(statements) <= 1):
                            logger.info("statements less than 2, skip")
                            continue
                        flow_item["flow"] = statements
                        flow_item["apis"] = encode_apis(flow["apis"])
                        flow_item["types"] = encode_types(flow["types"])
                        vfs_all.append(flow_item)
    with open(out_path, "w") as f:
        json.dump(vfs_all, f)


def build_d2a_method_vd(project: str):
    project_root = f"data/outputs/{project}"
    commitids = listdir(project_root)
    out_path = f"/home/chengxiao/project/ICSE22/data/vul_detect/d2a/{project}.json"
    prefix_p = "/home/chengxiao/project/ICSEDataSets"

    method_all = list()

    for commitid in commitids:
        funcid_to_method = dict()
        commit_root = join(project_root, commitid)
        logger.info(f"Processing {commit_root}..")
        label_path = join(commit_root, "label.json")
        if (exists(label_path)):
            with open(label_path, "r") as f:
                labels = json.load(f)
        else:
            logger.info(f"no label for {commit_root}")
            continue

        for i, label in enumerate(labels):

            # if label["source"] in ["auto1", "after0", "auto0"]:
            label_funcs = label["label_funcs"]
            for j, func in enumerate(label_funcs):
                funcid = func["file_path"] + "|" + func["method"][
                    0] + "|" + str(func["method"][1]) + "|" + str(
                        func["method"][2])
                if (funcid in funcid_to_method):
                    if (funcid_to_method[funcid] is not None):

                        if "method_trace" in func:
                            union_flaws = set(
                                funcid_to_method[funcid]["flaws"]).union(
                                    func["method_trace"])
                            funcid_to_method[funcid]["flaws"] = list(
                                union_flaws)
                    continue

                method_item = dict()
                method_item["label"] = label["label"]
                if "method_trace" in func:
                    method_item["flaws"] = func["method_trace"]
                else:
                    method_item["flaws"] = []
                if method_item["label"] == 1 and method_item["flaws"] == []:
                    continue
                if "flows" not in func:
                    continue
                graph_path = join(join(join(prefix_p, commit_root), "graphs"),
                                  func["file_path"])
                file_path = join(join(join(prefix_p, commit_root), "files"),
                                 func["file_path"])
                if (not exists(join(graph_path, "nodes.csv"))):
                    logger.info("no graph path, skip")
                    continue

                with open(file_path, "r", encoding="utf-8",
                          errors="ignore") as f:
                    file_content = f.readlines()

                method_item["files"] = [file_path]
                method_item["graph_paths"] = [graph_path]
                vfs = list()
                for flow in func["flows"]:
                    statements = list()
                    for st in flow["statements"]:

                        ln = int(st.split(",")[1])
                        if ln - 1 == len(file_content):
                            ln -= 1
                        if (ln - 1 >= len(file_content)):
                            logger.error(
                                f"{file_path} {str(func['method'])} {str(flow['statements'])} "
                            )
                            continue
                        if (file_content[ln - 1].strip() != ""):
                            statements.append("0," + str(ln))
                    if (len(statements) <= 1):
                        logger.info("statements less than 2, skip")
                        continue

                    vfs.append(statements)
                if vfs != []:
                    method_item["flows"] = vfs
                    funcid_to_method[funcid] = method_item
                else:
                    funcid_to_method[funcid] = None
        method_all.extend(funcid_to_method.values())
    with open(out_path, "w") as f:
        json.dump(method_all, f)


def split_dataset(file_path: str):
    all_json_path = join(file_path, "all.json")
    with open(all_json_path, "r") as f:
        all_data = json.load(f)
    X_train, X_val = train_test_split(all_data, test_size=0.2)
    X_val, X_detect = train_test_split(
        X_val,
        test_size=0.5,
    )
    with open(join(file_path, "train.json"), "w") as f:
        json.dump(X_train, f)
        logger.info(f"{len(X_train)} for training")
    with open(join(file_path, "val.json"), "w") as f:
        json.dump(X_val, f)
        logger.info(f"{len(X_val)} for validating")
    with open(join(file_path, "test.json"), "w") as f:
        json.dump(X_detect, f)
        logger.info(f"{len(X_detect)} for detecting")


if __name__ == "__main__":
    # extract_d2a_method_vfs("nginx")
    # cp_missed_files("nginx")
    # build_d2a_vfs_cl("nginx")
    build_d2a_method_vd("nginx")
    # split_dataset("/home/chengxiao/project/ICSE22/data/vul_detect/d2a/")