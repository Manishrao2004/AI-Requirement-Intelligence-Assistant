import re
from pathlib import Path
from typing import Union
from app.schemas import DocumentSection, ParsedDocument

# Lazy-loaded Docling converter to avoid slow startup
_doc_converter = None

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm", ".md", ".txt", ".asciidoc", ".adoc"}

def _get_converter():
    global _doc_converter
    if _doc_converter is None:
        from docling.document_converter import DocumentConverter
        _doc_converter = DocumentConverter()
    return _doc_converter


def parse_document(doc_path: Union[str, Path], filename: str) -> ParsedDocument:
    """Use Docling to convert any supported document into structured sections."""
    converter = _get_converter()
    result = converter.convert(str(doc_path))
    md_content = result.document.export_to_markdown()
    return _markdown_to_parsed_doc(md_content, filename)


def _markdown_to_parsed_doc(md_text: str, filename: str) -> ParsedDocument:
    lines = md_text.splitlines()
    doc_title = Path(filename).stem
    version = None
    if "v1" in filename.lower():
        version = "V1"
    elif "v2" in filename.lower():
        version = "V2"

    sections: list[DocumentSection] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        header_match = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if header_match:
            heading_text = re.sub(r'^[●\s\-\*]+', '', header_match.group(2)).strip()

            # First header becomes doc title
            if not sections and current_heading is None and not current_lines:
                doc_title = heading_text
                current_heading = heading_text
                continue

            # Save previous section
            if current_heading and current_lines:
                sections.append(DocumentSection(
                    heading=current_heading,
                    content="\n".join(current_lines).strip()
                ))
                current_lines = []

            current_heading = heading_text
        else:
            if current_heading is None:
                current_heading = "Overview"
            current_lines.append(line)

    # Final section
    if current_heading and current_lines:
        sections.append(DocumentSection(
            heading=current_heading,
            content="\n".join(current_lines).strip()
        ))

    return ParsedDocument(
        doc_id=filename,
        title=doc_title,
        version=version,
        sections=sections,
        full_text=md_text
    )


def chunk_document(doc: ParsedDocument) -> list[str]:
    """Split parsed document sections into analysis-ready text chunks."""
    chunks = []
    for section in doc.sections:
        chunk = f"## {section.heading}\n{section.content}"
        chunks.append(chunk)
    return chunks
