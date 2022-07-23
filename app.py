# coding:utf-8
import os
from pathlib import Path
import re
import unicodedata
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from flask_fuzhu.decorator import need_args
from flask_fuzhu.decorator import need_token
from flask_fuzhu.decorator import return_json
from flask_fuzhu.exception import BadRequest

load_dotenv(Path(".env"))
app = Flask(__name__)
CORS(app)
FILE_PATH = Path(os.environ.get("ATTACHMENT_PATH")) or Path("attachment")
if not FILE_PATH.exists():
    FILE_PATH.mkdir(parents=True)
ARGS_LIST_SEPARATOR = os.environ.get("ARGS_LIST_SEPARATOR ") or ","


def generate_uuid():
    return uuid4().hex


def secure_filename(filename: str) -> str:
    """链接：https://juejin.cn/post/6984687937036222471"""
    _windows_device_files = (
        "CON",
        "AUX",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "LPT1",
        "LPT2",
        "LPT3",
        "PRN",
        "NUL",
    )
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("utf8", "ignore").decode("utf8")  # 编码格式改变

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    _filename_ascii_add_strip_re = re.compile(r"[^A-Za-z0-9_\u4E00-\u9FBF\u3040-\u30FF\u31F0-\u31FF.-]")
    filename = str(_filename_ascii_add_strip_re.sub("", "_".join(filename.split()))).strip("._")  # 添加新规则

    # on nt a couple of special files are present in each folder.  We
    # have to ensure that the target file is not such a filename.  In
    # this case we prepend an underline
    if os.name == "nt" and filename and filename.split(".")[0].upper() in _windows_device_files:
        filename = f"_{filename}"

    return filename


@app.route("/upload", methods=["POST"])
@return_json
@need_token()
def upload():
    if "files[]" not in request.files:
        raise BadRequest(msg="文件上传表单格式错误")
    files = request.files.getlist("files[]")
    # bad_files = not_allowed_files(files)
    # if bad_files:
    #     raw = "，".join(bad_files)
    #     raise BadRequest(msg=f"这些文件的类型不允许上传: {raw}")

    # 指定 FILE_PATH 下的存储路径
    path = FILE_PATH
    sub_path = request.args.get("subpath", "")
    if sub_path != "" and not re.match("^[a-zA-Z0-9_/]+$", sub_path):
        raise BadRequest(msg="path字符不合法，合法字符：数字、字母、_、/")
    else:
        path = path / sub_path
        print(path)
        if not path.exists():
            path.mkdir(parents=True)

    ret = []
    for f in files:
        save_name = f"{generate_uuid()}.{f.filename.lower().split('.')[-1]}"
        f.save(str(path / save_name))
        ret.append({"source": secure_filename(f.filename), "target": save_name})
    return {"msg": f"成功上传了{len(files)}个文件。", "data": ret}, 201


@app.route("/delete", methods=["DELETE"])
@return_json
@need_args(["uid"])
@need_token(lambda token: token == "123321")
def delete():
    # 多个uid用,分隔
    uid_list = request.args.get("uid").split(ARGS_LIST_SEPARATOR)
    for f in FILE_PATH.iterdir():
        if f.stem in uid_list:
            f.unlink(missing_ok=True)
    return {"msg": f"成功删除{len(uid_list)}个文件。"}


if __name__ == "__main__":
    app.run()
