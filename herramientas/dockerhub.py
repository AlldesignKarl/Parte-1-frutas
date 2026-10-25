"""Inspecciona imágenes públicas de Docker Hub y extrae ficheros concretos de sus capas (sin ejecutar nada).
  dockerhub.py info repo[:tag]
  dockerhub.py list repo[:tag] layer_digest            -> lista ficheros de una capa
  dockerhub.py get repo[:tag] layer_digest patron outdir -> extrae ficheros que casen con el patrón"""
import json
import re
import subprocess
import sys
import tarfile
import urllib.request

ACC = ("application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,"
       "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json")


def token(repo):
    with urllib.request.urlopen(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull") as r:
        return json.load(r)["token"]


def get(repo, path, tok, accept=ACC):
    req = urllib.request.Request(f"https://registry-1.docker.io/v2/{repo}/{path}",
                                 headers={"Authorization": f"Bearer {tok}", "Accept": accept})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def manifest(ref):
    repo, _, tag = ref.partition(":")
    tag = tag or "latest"
    if "/" not in repo:
        repo = "library/" + repo
    tok = token(repo)
    m = get(repo, f"manifests/{tag}", tok)
    if "manifests" in m:
        d = [x for x in m["manifests"] if x.get("platform", {}).get("architecture") == "amd64"][0]["digest"]
        m = get(repo, f"manifests/{d}", tok)
    return repo, tok, m


def info(ref):
    repo, tok, m = manifest(ref)
    cfg = get(repo, f"blobs/{m['config']['digest']}", tok, "*/*")
    hist = [h for h in cfg.get("history", []) if not h.get("empty_layer")]
    tot = 0
    for i, l in enumerate(m["layers"]):
        cb = hist[i].get("created_by", "") if i < len(hist) else ""
        tot += l["size"]
        print(f"{l['digest'][:19]}  {l['size'] / 1e6:9.1f} MB  {cb[:150]}")
    print(f"total {tot / 1e9:.2f} GB")


def stream(repo, tok, digest):
    url = f"https://registry-1.docker.io/v2/{repo}/blobs/{digest}"
    p = subprocess.Popen(["curl", "-sL", "-H", f"Authorization: Bearer {tok}", url], stdout=subprocess.PIPE)
    return p


def full_digest(m, short):
    return [l["digest"] for l in m["layers"] if l["digest"].startswith(short)][0]


def list_layer(ref, short):
    repo, tok, m = manifest(ref)
    p = stream(repo, tok, full_digest(m, short))
    with tarfile.open(fileobj=p.stdout, mode="r|*") as tf:
        for ti in tf:
            if ti.size > 1e6:
                print(f"{ti.size / 1e6:9.1f} MB  {ti.name}")


def get_files(ref, short, pattern, outdir):
    import os
    repo, tok, m = manifest(ref)
    p = stream(repo, tok, full_digest(m, short))
    rx = re.compile(pattern)
    with tarfile.open(fileobj=p.stdout, mode="r|*") as tf:
        for ti in tf:
            if ti.isfile() and rx.search(ti.name):
                dst = os.path.join(outdir, os.path.basename(ti.name))
                with tf.extractfile(ti) as src, open(dst, "wb") as out:
                    while True:
                        b = src.read(1 << 20)
                        if not b:
                            break
                        out.write(b)
                print("extraído", ti.name, f"{ti.size / 1e6:.1f} MB")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "info":
        info(sys.argv[2])
    elif cmd == "list":
        list_layer(sys.argv[2], sys.argv[3])
    elif cmd == "get":
        get_files(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
