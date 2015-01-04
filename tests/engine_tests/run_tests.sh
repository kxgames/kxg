#!/usr/bin/env sh

python -m coverage run --source kxg.engine test_forum_and_actor.py
python -m coverage html
