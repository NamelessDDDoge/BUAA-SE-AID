import os
import zipfile
from pathlib import Path

def pack_python_files(source_folder, output_zip_path):
    """
    查找指定文件夹下的所有.py文件，按原始目录结构打包成zip文件
    
    Args:
        source_folder (str): 源文件夹路径
        output_zip_path (str): 输出的zip文件路径
    """
    source_path = Path(source_folder)
    
    if not source_path.exists():
        print(f"错误：源文件夹 '{source_folder}' 不存在")
        return False
    
    # 创建zip文件
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        py_files_count = 0
        
        # 递归遍历所有文件
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                if file.endswith('.py'):
                    # 获取完整文件路径
                    file_path = os.path.join(root, file)
                    
                    # 计算相对路径（保持原始目录结构）
                    relative_path = os.path.relpath(file_path, source_folder)
                    
                    # 添加到zip文件
                    zipf.write(file_path, relative_path)
                    py_files_count += 1
                    print(f"已添加: {relative_path}")
        
        print(f"\n打包完成！共处理了 {py_files_count} 个Python文件")
        print(f"压缩包保存至: {output_zip_path}")
        
    return True

def pack_python_files_with_pathlib(source_folder, output_zip_path):
    """
    使用pathlib的替代实现方案
    
    Args:
        source_folder (str): 源文件夹路径
        output_zip_path (str): 输出的zip文件路径
    """
    source_path = Path(source_folder)
    
    if not source_path.exists():
        print(f"错误：源文件夹 '{source_folder}' 不存在")
        return False
    
    # 查找所有.py文件
    py_files = list(source_path.rglob('*.py'))
    
    if not py_files:
        print("未找到任何Python文件")
        return False
    
    # 创建zip文件
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for py_file in py_files:
            # 计算相对路径
            relative_path = py_file.relative_to(source_path)
            
            # 添加到zip文件
            zipf.write(py_file, relative_path)
            print(f"已添加: {relative_path}")
    
    print(f"\n打包完成！共处理了 {len(py_files)} 个Python文件")
    print(f"压缩包保存至: {output_zip_path}")
    
    return True

# 使用示例
if __name__ == "__main__":
    # 设置源文件夹和输出文件路径
    source_folder = input("请输入要扫描的文件夹路径: ").strip()
    if not source_folder:
        source_folder = "."  # 默认当前目录
    
    output_zip = input("请输入输出的zip文件名 (默认: python_files.zip): ").strip()
    if not output_zip:
        output_zip = "python_files.zip"
    
    # 确保zip文件有正确的扩展名
    if not output_zip.endswith('.zip'):
        output_zip += '.zip'
    
    print(f"\n开始扫描文件夹: {os.path.abspath(source_folder)}")
    print("="*50)
    
    # 执行打包操作
    success = pack_python_files(source_folder, output_zip)
    
    if success:
        print("="*50)
        print("操作完成！")
    else:
        print("操作失败！")
