"""Train and score one fold on a Modal GPU (26 Oct 2026: the author's Mac cannot hold the 8B, the HPC login is not at
hand, and the Modal workspace already runs the collectors).

    OSWorld/.venv/bin/modal run rig/train/modal_train.py --folds 0                 # fold 0 alone: the smoke test
    OSWorld/.venv/bin/modal run rig/train/modal_train.py --folds 1,2,3,4 --parallel
    OSWorld/.venv/bin/modal run rig/train/modal_train.py --folds 0 --train-file /data/subsets/fold0_rows50.jsonl --tag _rows50

Data (rig/train/data_k3, data_k1, subsets/) and the two scripts ride in the image; the Hugging Face cache and every
run's adapter and scores live on the volume "osguard-train" under /vol; scores are also written locally to
rig/train/runs/modal/<tag>/fold<N>.json.  One fold of Qwen3-8B, rank 32, 3 epochs, is minutes on an A100-80GB.
"""
import json
import pathlib
import subprocess

import modal

HERE = pathlib.Path(__file__).parent
app = modal.App("osguard-train")
vol = modal.Volume.from_name("osguard-train", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install_from_requirements(str(HERE / "requirements.txt"))
         .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
         .add_local_dir(str(HERE / "data_k3"), remote_path="/data/k3")
         .add_local_dir(str(HERE / "data_k1"), remote_path="/data/k1")
         .add_local_dir(str(HERE / "data_k3_v3"), remote_path="/data/k3_v3")
         .add_local_dir(str(HERE / "subsets"), remote_path="/data/subsets")
         .add_local_file(str(HERE / "train_lora.py"), remote_path="/code/train_lora.py")
         .add_local_file(str(HERE / "evaluate.py"), remote_path="/code/evaluate.py"))


@app.function(image=image, gpu="A100-80GB", timeout=3 * 3600, volumes={"/vol": vol})
def run_fold(fold: int, k: int = 3, model: str = "Qwen/Qwen3-8B", rank: int = 32, epochs: float = 3.0,
             train_file: str = "", tag: str = "", seed: int = 2026, data: str = "") -> dict:
    """data: suffix of the mounted data set, '' for /data/k{k} (the 26 Oct export) or '_v3' for /data/k3_v3 (with the
    v3 one-way rows of 26-27 Oct)."""
    out = f"/vol/runs/k{k}{tag}/fold{fold}"
    train = train_file or f"/data/k{k}{data}/fold{fold}_train.jsonl"
    test = f"/data/k{k}{data}/fold{fold}_test.jsonl"
    subprocess.run(["python", "/code/train_lora.py", "--train", train, "--eval", test, "--model", model,
                    "--rank", str(rank), "--epochs", str(epochs), "--seed", str(seed), "--out", out], check=True)
    subprocess.run(["python", "/code/evaluate.py", "--test", test, "--model", model, "--adapter", out + "/adapter",
                    "--out", out + "/scores.json"], check=True)
    vol.commit()
    scores = json.load(open(out + "/scores.json"))
    scores["_run"] = {"fold": fold, "k": k, "model": model, "rank": rank, "epochs": epochs, "train": train, "test": test, "out": out, "seed": seed}
    return scores


@app.local_entrypoint()
def main(folds: str = "0", k: int = 3, model: str = "Qwen/Qwen3-8B", rank: int = 32, epochs: float = 3.0,
         train_file: str = "", tag: str = "", parallel: bool = False, seed: int = 2026, data: str = ""):
    fl = [int(f) for f in folds.split(",")]
    kw = dict(k=k, model=model, rank=rank, epochs=epochs, train_file=train_file, tag=tag, seed=seed, data=data)
    if parallel and len(fl) > 1:
        results = list(run_fold.starmap([(f,) for f in fl], kwargs=kw))
    else:
        results = [run_fold.remote(f, **kw) for f in fl]
    dest = HERE / "runs" / "modal" / f"k{k}{tag}"
    dest.mkdir(parents=True, exist_ok=True)
    for f, r in zip(fl, results):
        (dest / f"fold{f}.json").write_text(json.dumps(r, indent=1))
        print(f"fold {f}:", json.dumps({t: v for t, v in r.items() if t in ("REVERSIBLE", "GUARD", "UNDO")}))
