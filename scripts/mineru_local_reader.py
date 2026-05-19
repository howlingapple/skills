#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 MinerU PDF 解析器 (3.x 版本)

使用 mineru 包进行 PDF 解析，无需 API。
支持布局分析、表格识别、公式识别、OCR。
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Union

# 设置 MinerU 模型路径（使用项目本地模型）
_script_dir = os.path.dirname(os.path.abspath(__file__))
_mineru_home = os.path.join(_script_dir, "..", ".mineru")
os.makedirs(_mineru_home, exist_ok=True)

# MinerU 3.x 模型定位配置
_mineru_config = os.path.join(_mineru_home, "mineru.json")
os.environ["MINERU_MODEL_SOURCE"] = "local"
os.environ["MINERU_TOOLS_CONFIG_JSON"] = _mineru_config

# ---- fast-langdetect 兼容层 ----
# fasttext-predict 的 C++ 扩展不支持含 CJK 字符的路径，
# 将 lid.176.ftz 复制到 ASCII 临时目录以绕过此限制。
_fasttext_model_src = (
    Path(__file__).parent.parent / ".venv" / "Lib" / "site-packages"
    / "fast_langdetect" / "ft_detect" / "resources" / "lid.176.ftz"
)
if not _fasttext_model_src.exists():
    # 尝试从当前 .venv 查找
    _venv_root = Path(sys.prefix)
    _fasttext_model_src = (
        _venv_root / "Lib" / "site-packages"
        / "fast_langdetect" / "ft_detect" / "resources" / "lid.176.ftz"
    )

if _fasttext_model_src.exists():
    _fasttext_cache = Path(tempfile.gettempdir()) / "mineru_fasttext"
    _fasttext_cache.mkdir(parents=True, exist_ok=True)
    _fasttext_model_dst = _fasttext_cache / "lid.176.ftz"
    if not _fasttext_model_dst.exists():
        shutil.copy2(str(_fasttext_model_src), str(_fasttext_model_dst))
    # 替换 fast-langdetect 的模型路径为无 CJK 路径
    import fast_langdetect.ft_detect.infer as _ft_infer
    _ft_infer.LOCAL_SMALL_MODEL_PATH = _fasttext_model_dst
    # 缓存目录同样设为 ASCII 路径，避免下载的大模型也遇到此问题
    os.environ.setdefault("FTLANG_CACHE", str(_fasttext_cache))

from llama_index.core.schema import Document


class MinerULocalReader:
    """本地 MinerU PDF 解析器 (3.x)"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        enable_ocr: bool = False,
        enable_formula: bool = True,
        enable_table: bool = True,
        split_pages: bool = True,
        lang: str = "ch",
    ):
        self.device = device
        self.enable_ocr = enable_ocr
        self.enable_formula = enable_formula
        self.enable_table = enable_table
        self.split_pages = split_pages
        self.model_path = model_path
        self.lang = lang

    def load_data(self, file_path: Union[str, Path, List[str]]) -> List[Document]:
        """
        解析 PDF 文件，返回 Document 列表

        Args:
            file_path: 单个 PDF 路径或路径列表

        Returns:
            List[Document]: 解析后的文档列表
        """
        from mineru.cli.common import do_parse

        # 统一处理为列表
        if isinstance(file_path, (str, Path)):
            file_paths = [Path(file_path)]
        else:
            file_paths = [Path(fp) for fp in file_path]

        all_documents = []
        temp_output_dir = Path(_mineru_home) / "temp_output"
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        for fp in file_paths:
            if not fp.exists():
                print(f"[MinerULocalReader] 文件不存在: {fp}", file=sys.stderr)
                continue

            if fp.suffix.lower() != ".pdf":
                print(f"[MinerULocalReader] 跳过非 PDF 文件: {fp}", file=sys.stderr)
                continue

            # 读取 PDF 文件
            try:
                print(f"[MinerULocalReader] 开始解析: {fp}", file=sys.stderr)

                pdf_bytes = fp.read_bytes()
                pdf_file_name = fp.name

                # do_parse 内部会用 prepare_env 创建子目录:
                #   output_dir / pdf_file_name / parse_method /
                # 所以 output_dir 直接传 temp_output_dir 即可
                parse_method = "ocr" if self.enable_ocr else "auto"
                do_parse(
                    output_dir=str(temp_output_dir),
                    pdf_file_names=[pdf_file_name],
                    pdf_bytes_list=[pdf_bytes],
                    p_lang_list=[self.lang],
                    backend="pipeline",
                    parse_method=parse_method,
                    formula_enable=self.enable_formula,
                    table_enable=self.enable_table,
                    f_draw_layout_bbox=False,
                    f_draw_span_bbox=False,
                    f_dump_md=True,
                    f_dump_middle_json=False,
                    f_dump_model_output=False,
                    f_dump_orig_pdf=False,
                    f_dump_content_list=False,
                )

                # 读取生成的 markdown 文件
                docs = self._read_output(temp_output_dir, pdf_file_name, parse_method, fp)
                all_documents.extend(docs)

                print(f"[MinerULocalReader] 解析完成: {fp} -> {len(docs)} 页", file=sys.stderr)

            except Exception as e:
                print(f"[MinerULocalReader] 解析失败 {fp}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

        return all_documents

    def _read_output(self, temp_output_dir: Path, pdf_file_name: str, parse_method: str, original_path: Path) -> List[Document]:
        """读取 MinerU 生成的输出文件"""
        documents = []

        # MinerU prepare_env 创建的实际路径: output_dir / pdf_file_name / parse_method /
        # md_writer 在 local_md_dir 下写入 pdf_file_name.md
        md_dir = temp_output_dir / pdf_file_name / parse_method
        md_file = md_dir / f"{pdf_file_name}.md"

        if md_file.exists():
            content = md_file.read_text(encoding="utf-8")

            if self.split_pages:
                # 按页拆分（根据 MinerU 的输出格式）
                # MinerU 3.x 默认按页面生成内容，用特定分隔符
                pages = self._split_by_pages(content)
                for i, page_content in enumerate(pages, 1):
                    if page_content.strip():
                        # 将来源和页码嵌入文本开头
                        source_info = f"【文本来源：（文件名：{original_path.name}，页码：{i}）】\n"
                        full_text = source_info + page_content.strip()
                        documents.append(Document(
                            text=full_text,
                            metadata={
                                "source": str(original_path),
                                "page": i,
                            }
                        ))
            else:
                documents.append(Document(
                    text=content,
                    metadata={"source": str(original_path)}
                ))
        else:
            print(f"[MinerULocalReader] 警告: 未找到输出文件 {md_file}", file=sys.stderr)

        return documents

    def _split_by_pages(self, content: str) -> List[str]:
        """按页面拆分内容"""
        # MinerU 3.x 输出格式可能有多种分隔方式
        # 尝试常见的分隔符
        
        # 方式1: 使用 --- 分隔
        if "\n---\n" in content:
            return [p.strip() for p in content.split("\n---\n") if p.strip()]
        
        # 方式2: 使用分页符
        if "\f" in content:
            return [p.strip() for p in content.split("\f") if p.strip()]
        
        # 方式3: 使用标题作为分页标记 (# 开头)
        import re
        # 查找所有一级标题作为分页点
        pages = re.split(r'\n(?=#\s)', content)
        return [p.strip() for p in pages if p.strip()]


# 兼容 LlamaIndex 的 load_data 接口
def load_mineru_local(
    file_path: Union[str, Path, List[str]],
    model_path: Optional[str] = None,
    device: str = "cpu",
    enable_ocr: bool = False,
    enable_formula: bool = True,
    enable_table: bool = True,
    split_pages: bool = True,
    lang: str = "ch",
) -> List[Document]:
    """
    便捷函数：直接加载 PDF

    Example:
        >>> docs = load_mineru_local("document.pdf")
        >>> docs = load_mineru_local(["doc1.pdf", "doc2.pdf"], enable_table=True)
    """
    reader = MinerULocalReader(
        model_path=model_path,
        device=device,
        enable_ocr=enable_ocr,
        enable_formula=enable_formula,
        enable_table=enable_table,
        split_pages=split_pages,
        lang=lang,
    )
    return reader.load_data(file_path)


if __name__ == "__main__":
    # 简单测试
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"[Test] 解析 PDF: {pdf_path}")

        reader = MinerULocalReader(
            enable_table=True,
            enable_formula=True,
            split_pages=True,
        )
        docs = reader.load_data(pdf_path)

        print(f"[Test] 解析完成，共 {len(docs)} 页/文档")
        for i, doc in enumerate(docs[:3]):  # 只显示前 3 页
            print(f"\n--- 第 {i+1} 页 ---")
            print(doc.text[:500] + "..." if len(doc.text) > 500 else doc.text)
    else:
        print("用法: python mineru_local_reader.py <pdf_path>")
