import sys
import os
import logging
#import wakeonlan
import argparse

from samsungtvws import SamsungTVWS

# Increase debug level
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

def openb(arg):
    """open as binary, used by argparse"""
    return open(arg, 'rb')

def get_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_list = subparsers.add_parser("list", help="list art")
    parser_list.set_defaults(func=do_list)

    parser_set = subparsers.add_parser("set", help="pick art")
    parser_set.add_argument("name", type=str)
    parser_set.set_defaults(func=do_set)

    parser_upload = subparsers.add_parser("upload", help="upload")
    parser_upload.add_argument("filename", type=openb)
    parser_upload.add_argument("--no-switch, -n", help="Don't switch to this uploaded file", type=bool, dest="noswitch")
    parser_upload.set_defaults(func=do_upload, noswitch=False)

    parser_delete = subparsers.add_parser("delete", help="delete by name")
    parser_delete.add_argument("name", type=str)
    parser_delete.set_defaults(func=do_delete)

    args = parser.parse_args()
    if not args:
        parser.print_help()
        sys.exit(2)
    return args


def do_list(args: argparse.Namespace):
    tv = get_tv()
    info = tv.art().available()
    if not info:
        print("No content")
    for item in info:
        print(f'{item["content_id"]}\t{item.get("width", "0")}x{item.get("height", "0")}\ttype={item["content_type"]}')

def get_tv():
    tv_ip = os.getenv("FRAME_IP")
    if not tv_ip:
        print("FRAME_IP not provided", file=sys.stderr)
        sys.exit(1)

    # Normal constructor
    return SamsungTVWS(tv_ip)

def do_upload(args: argparse.Namespace):
    tv = get_tv()
    logging.info("Uploading")
    data = args.filename.read()

    image_name = tv.art().upload(data, matte="none", portrait_matte="none")
    logging.info(f"Uploaded {image_name}")

    if not args.noswitch:
        logging.info("Switching to new image")
        tv.art().select_image(image_name)
    print(image_name)


def do_set(args: argparse.Namespace):
    tv = get_tv()
    if not args.name:
        print("name is required", file=sys.stderr)
        sys.exit(2)
    resp = tv.art().select_image(args.name)
    logging.info(resp)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def do_delete(args: argparse.Namespace):
    tv = get_tv()
    if not args.name:
        print("name is required", file=sys.stderr)
        sys.exit(2)
    names = args.name.split(',')
    for ns in chunks(names, 5):
        print(f'deleting {ns}', file=sys.stderr)
        resp = tv.art().delete_list(ns)
        logging.info(resp)


if __name__ == '__main__':
    args = get_args()
    args.func(args)
