#!/bin/bash
cd nginx
nohup ./auto/configure --with-cc=clang --with-cpp=clang++  &
nohup make -j8 &
cd ..