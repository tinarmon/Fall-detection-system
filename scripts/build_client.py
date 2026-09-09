"""Standalone bytecode packaging script for Windows PyInstaller distribution."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile


def get_python_exe() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(base_dir, "venv", "Scripts", "python.exe"),
        sys.executable,
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return sys.executable


def zip_dir(src_dir: str, zip_file_path: str) -> None:
    try:
        subprocess.run(
            ["tar", "-a", "-cf", zip_file_path, "-C", src_dir, "."],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (subprocess.SubprocessError, OSError):
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(src_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, src_dir)
                    zipf.write(abs_path, rel_path)


def build() -> None:
    python_exe = get_python_exe()
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    installer_dir = os.path.join(project_dir, "InstallerFile")
    dist_dir = os.path.join(project_dir, "dist")
    build_dir = os.path.join(project_dir, "build")

    lightweight_excludes = [
        "--exclude-module=cv2",
        "--exclude-module=numpy",
        "--exclude-module=matplotlib",
        "--exclude-module=tensorflow",
        "--exclude-module=mediapipe",
        "--exclude-module=scipy",
        "--exclude-module=PIL",
        "--exclude-module=pandas",
        "--exclude-module=torch",
    ]

    for folder in [build_dir, dist_dir]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except OSError:
                pass

    os.makedirs(installer_dir, exist_ok=True)

    subprocess.run(
        [
            python_exe,
            "-m",
            "PyInstaller",
            "main.py",
            "--name=DPDF",
            "--onedir",
            "--noconsole",
            "--clean",
            "--collect-all=mediapipe",
            "--copy-metadata=mediapipe",
            "--add-data=assets;assets",
            "--add-data=configs;configs",
            "--icon=assets/icon.ico",
        ],
        check=True,
        cwd=project_dir,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )

    subprocess.run(
        [
            python_exe,
            "-m",
            "PyInstaller",
            "uninstall_gui.py",
            "--name=uninstall",
            "--onefile",
            "--noconsole",
            "--clean",
            "--noupx",
            "--icon=assets/icon.ico",
            f"--distpath={os.path.join(dist_dir, 'DPDF')}",
        ]
        + lightweight_excludes,
        check=True,
        cwd=project_dir,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )

    dest_assets = os.path.join(dist_dir, "DPDF", "assets")
    src_assets = os.path.join(project_dir, "assets")
    if os.path.exists(src_assets):
        shutil.copytree(src_assets, dest_assets, dirs_exist_ok=True)

    dest_configs = os.path.join(dist_dir, "DPDF", "configs")
    src_configs = os.path.join(project_dir, "configs")
    if os.path.exists(src_configs):
        shutil.copytree(src_configs, dest_configs, dirs_exist_ok=True)

    zip_path = os.path.join(project_dir, "payload.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    zip_dir(os.path.join(dist_dir, "DPDF"), zip_path)

    subprocess.run(
        [
            python_exe,
            "-m",
            "PyInstaller",
            "setup_gui.py",
            "--name=DPDF_Setup",
            "--onefile",
            "--noconsole",
            f"--add-data={zip_path};.",
            "--clean",
            "--noupx",
            "--icon=assets/icon.ico",
            f"--distpath={installer_dir}",
        ]
        + lightweight_excludes,
        check=True,
        cwd=project_dir,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )

    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
        except OSError:
            pass


if __name__ == "__main__":
    build()
