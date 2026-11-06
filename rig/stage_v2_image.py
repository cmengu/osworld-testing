"""Stage the OSWorld 2.1 Ubuntu disk into our Modal Volume (6 Nov 2026, author's go: "lets try").

OSWorld-V2's Docker provider runs the same runner image as v1 (happysixd/osworld-docker, pinned by digest) with a new
qcow2, so our Modal provider only needs that disk.  The zip is public on Hugging Face (14.9 GB, pinned revision below,
same URL as OSWorld-V2 desktop_env/providers/docker/manager.py at tag osworld-v2.1).  The download, unzip and copy
run in one Modal function with a large scratch disk.  It is skipped if the file is already in the Volume.

    OSWorld/.venv/bin/python -I rig/stage_v2_image.py
"""
import modal

URL = ("https://huggingface.co/datasets/xlangai/v2-image/resolve/6e16459a2feb5a8f1ed65babcfe7a2a6205d049d/"
       "osworld-v2-ubuntu-x86.qcow2.zip")
NAME = "osworld-v2-ubuntu-x86.qcow2"
VOLUME = modal.Volume.from_name("osworld-vm-images", version=2)
app = modal.App("osworld-staging-v2")


@app.function(image=modal.Image.debian_slim().apt_install("unzip", "curl", "qemu-utils"), volumes={"/vm": VOLUME},
              timeout=3 * 3600, cpu=2, memory=4096, ephemeral_disk=512 * 1024)
def stage():
    import glob, os, shutil, subprocess
    target = f"/vm/{NAME}"
    if os.path.exists(target):
        return f"already present: {os.path.getsize(target)} B"
    subprocess.run(["curl", "-sSL", "--retry", "5", "-o", "/tmp/img.zip", URL], check=True)
    print("zip", os.path.getsize("/tmp/img.zip"), flush=True)
    subprocess.run(["unzip", "-q", "-o", "/tmp/img.zip", "-d", "/tmp/stage"], check=True)
    os.remove("/tmp/img.zip")
    src = glob.glob("/tmp/stage/**/*.qcow2", recursive=True)[0]
    info = subprocess.run(["qemu-img", "info", src], capture_output=True, text=True).stdout
    print(info, flush=True)
    shutil.copyfile(src, target + ".part")
    os.rename(target + ".part", target)
    VOLUME.commit()
    return f"staged {os.path.getsize(target)} B from {os.path.basename(src)}\n{info}"


if __name__ == "__main__":
    with modal.enable_output(), app.run():
        print(stage.remote())
