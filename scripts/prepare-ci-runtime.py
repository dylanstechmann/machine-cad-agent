"""Derive a CI Dockerfile using the same immutable Docker Official Image on ECR."""

import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
source = (root/"Dockerfile").read_text(encoding="utf-8")
first = source.splitlines()[0]
if not re.fullmatch(r"FROM python:[a-zA-Z0-9._-]+@sha256:[a-f0-9]{64}", first):
    raise ValueError("Expected one pinned Python base; review the CI mirror mapping before updating it")
derived = source.replace("FROM python:","FROM public.ecr.aws/docker/library/python:",1)
directory = root/"builds"
directory.mkdir(exist_ok=True)
(directory/"ci.Dockerfile").write_text(derived,encoding="utf-8")
print(derived.splitlines()[0])
