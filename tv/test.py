import sys
import os
import logging
#import wakeonlan
import argparse

from samsungtvws import SamsungTVWS

# Increase debug level
logging.basicConfig(level=logging.INFO)

def get_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_list = subparsers.add_parser("list", help="list art")
    parser_list.set_defaults(func=do_list)

    parser_set = subparsers.add_parser("set", help="pick art")
    parser_set.add_argument("name", type=str)
    parser_set.set_defaults(func=do_set)

    parser_upload = subparsers.add_parser("upload", help="upload")
    parser_upload.add_argument("filename", type=open)
    parser_upload.add_argument("--noswitch, -n", help="Don't switch to this uploaded file", type=bool)
    parser_upload.set_defaults(func=do_upload)

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
        print(f'{item["content_id"]}\t{item["width"]}x{item["height"]}\ttype={item["content_type"]}')

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

    image_name = tv.art().upload(data)
    logging.info(f"Uploaded {image_name}")

    if not args.noswitch:
        tv.art().select_image(image_name)


def do_set(args: argparse.Namespace):
    tv = get_tv()
    if not args.name:
        print("name is required", file=sys.stderr)
        sys.exit(2)
    resp = tv.art().select_image(args.name)
    logging.info(resp)


def do_delete(args: argparse.Namespace):
    tv = get_tv()
    if not args.name:
        print("name is required", file=sys.stderr)
        sys.exit(2)
    resp = tv.art().delete(args.name)
    logging.info(resp)

args = get_args()
args.func(args)
