#!/usr/bin/env python3

import os
import subprocess


ANSIBLE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ROOT_DIRECTORY = os.path.dirname(ANSIBLE_DIRECTORY)
FILES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "_site")


def main():
    os.chdir(ANSIBLE_DIRECTORY)
    key_file = os.path.join(ANSIBLE_DIRECTORY, "ssh_key")
    with open(key_file, "w") as fh:
        fh.write(os.environ["ANSIBLE_SSH_KEY"])
        fh.write("\n")
    os.chmod(key_file, 0o400)
    try:
        subprocess.check_call([
            "ansible-playbook",
            "-vvvv",
            "-i", "hosts",
            "index.yml",
            "--extra-vars", f"root={FILES_DIRECTORY}",
            "--extra-vars", f"ansible_ssh_private_key_file={key_file}",
            "--extra-vars", "ansible_become_pass='{{ lookup(\"env\", \"ANSIBLE_BECOME_PASS\") }}'",
       ])
    finally:
        os.remove(key_file)

if __name__ == "__main__":
    main()
