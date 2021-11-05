# ICSEDataSets

install dependencies and clone open-sourced projects:

```sh
git clone git@github.com:guanqin-123/ICSEDataSets.git
cd ICSEDataSets
bash env.sh
```

## Data Resources 

- D2A dataset hosted on [IBM Data Asset](https://developer.ibm.com/exchanges/data/all/d2a/).

- D2A description on [Github IBM/D2A](https://github.com/ibm/D2A#sample-description-and-dataset-stats).

- D2A dataset bug commits are classified in two types: Samples from the fixed versions.
Such samples are not directly generated from static analysis outputs because they are not reported by the analyzer. 
Therefore, they do not contain static analyzer outputs. Instead, given samples with positive auto-labeler labels 
(i.e. label_source == "auto_labeler" && label == 1) found in the before-fix version, 
we extract the corresponding functions in the after-fix version and label them 0 (e.g., after_fix_0.json). 
We use "label_source": "after_fix_extractor" to denote such samples. More information can be found in the Sec.III-D in the D2A paper.

## This Repo

- You can follow this tutorial to generate before-fix version (label = 1).

- Your target is to generate after-fix version (label = 0). 

## Data's Source code 

- https://github.com/libav/libav
- https://github.com/nginx/nginx
- https://github.com/apache/httpd
- https://gitlab.com/libtiff/libtiff
- https://github.com/openssl/openssl

## You need to do:

```shell
python3 src/d2a_label.py $project
python3 src/labeler.py $project
```

