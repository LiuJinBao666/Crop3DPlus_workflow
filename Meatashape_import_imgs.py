import Metashape
import os

# 支持的图片扩展名
IMAGE_EXTS = {
    ".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp"
}

def get_unique_chunk_label(doc, base_label):
    """
    如果 chunk 名称重复，自动加后缀：
    name
    name_01
    name_02
    """
    existing = {chunk.label for chunk in doc.chunks if chunk.label}

    if base_label not in existing:
        return base_label

    index = 1
    while True:
        new_label = f"{base_label}_{index:02d}"
        if new_label not in existing:
            return new_label
        index += 1


def collect_images(folder):
    """
    收集当前文件夹中的所有图片（不递归）
    """
    files = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGE_EXTS:
                files.append(path)
    return files


def find_whitebg_folders(root_dir):
    """
    递归查找所有名为 whitebg 的文件夹
    """
    whitebg_folders = []
    for current_root, dirs, files in os.walk(root_dir):
        if os.path.basename(current_root).lower() == "whitebg":
            whitebg_folders.append(current_root)

    whitebg_folders.sort()
    return whitebg_folders


def main():
    # 弹窗选择根目录
    root_dir = Metashape.app.getExistingDirectory("请选择项目根目录")

    if not root_dir:
        print("已取消选择文件夹，脚本结束。")
        return

    if not os.path.isdir(root_dir):
        raise Exception(f"选择的路径不是有效文件夹: {root_dir}")

    doc = Metashape.app.document

    whitebg_folders = find_whitebg_folders(root_dir)

    if not whitebg_folders:
        Metashape.app.messageBox("没有找到任何名为 whitebg 的文件夹。")
        return

    created_count = 0
    skipped_count = 0

    print(f"根目录: {root_dir}")
    print(f"找到 {len(whitebg_folders)} 个 whitebg 文件夹")

    for whitebg_dir in whitebg_folders:
        parent_folder = os.path.basename(os.path.dirname(whitebg_dir))
        images = collect_images(whitebg_dir)

        if not images:
            print(f"[跳过] whitebg 中没有图片: {whitebg_dir}")
            skipped_count += 1
            continue

        chunk = doc.addChunk()
        chunk.label = get_unique_chunk_label(doc, parent_folder)
        chunk.addPhotos(images)

        created_count += 1
        print(f"[完成] Chunk: {chunk.label} | 导入 {len(images)} 张照片")
        Metashape.app.update()

    msg = f"完成！\n新建 chunk: {created_count}\n跳过: {skipped_count}"
    print(msg)
    Metashape.app.messageBox(msg)


main()