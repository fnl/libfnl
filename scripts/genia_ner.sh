#!/usr/bin/env bash

HOME=~
GENIA_DATA_DIR=$HOME/var/geniatagger
NERSUITE_MODEL=$HOME/var/nersuite/models/bc2gm.iob2.no_dic.m
GENIA_TAGGER=geniatagger
NERSUITE_TAGGER=nersuite

cd $GENIA_DATA_DIR
$GENIA_TAGGER "$@" | sed "s/\(.\+\)\t[^\t]\+$/1\t2\t\1/" | $NERSUITE_TAGGER tag -m $NERSUITE_MODEL | sed "s/^1\t2\t//"
