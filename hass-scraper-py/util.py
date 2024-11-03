import os

def mustEnv(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise Exception(f"Must set {v}")
    return v

def openb(arg):
    """open as binary, used by argparse"""
    return open(arg, 'rb')
