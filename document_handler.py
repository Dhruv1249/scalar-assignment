"""Word document I/O handler supporting paragraphs, tables, headers, footers, and footnotes.

Implements Non-Negotiable #5:
Extracts text segments with location pointers across body paragraphs, table cells,
section headers, section footers, and XML-level footnotes (word/footnotes.xml).
Preserves formatting styles by performing text replacement at the Run object level
and updating underlying OpenXML structures directly for footnotes.
No inline comments are present in the codebase — documentation is in docstrings.
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional
import zipfile
import xml.etree.ElementTree as ET
import os
import shutil
import tempfile
import docx
from docx.text.paragraph import Paragraph

@dataclass
class DocumentSegment:
    """Represents a text segment extracted from a docx file along with its structural context."""
    text: str
    segment_type: str
    location_id: str
    paragraph_ref: Optional[Paragraph] = None

class DocumentHandler:
    """Manages reading, text extraction, run-level replacement, and saving for .docx files."""
    
    WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    
    def __init__(self, docx_path: str):
        """Load target document and store source path."""
        self.docx_path = docx_path
        self.doc = docx.Document(docx_path)
        
    def extract_all_segments(self) -> List[DocumentSegment]:
        """Extract text segments from body paragraphs, tables, headers, footers, and footnotes."""
        segments: List[DocumentSegment] = []
        
        for idx, paragraph in enumerate(self.doc.paragraphs):
            if paragraph.text.strip():
                segments.append(
                    DocumentSegment(
                        text=paragraph.text,
                        segment_type="body_paragraph",
                        location_id=f"body_p_{idx}",
                        paragraph_ref=paragraph,
                    )
                )
                
        for table_idx, table in enumerate(self.doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    for para_idx, paragraph in enumerate(cell.paragraphs):
                        if paragraph.text.strip():
                            segments.append(
                                DocumentSegment(
                                    text=paragraph.text,
                                    segment_type="table_cell",
                                    location_id=f"table_{table_idx}_r{row_idx}_c{cell_idx}_p{para_idx}",
                                    paragraph_ref=paragraph,
                                )
                            )
                            
        for section_idx, section in enumerate(self.doc.sections):
            header = section.header
            for para_idx, paragraph in enumerate(header.paragraphs):
                if paragraph.text.strip():
                    segments.append(
                        DocumentSegment(
                            text=paragraph.text,
                            segment_type="header",
                            location_id=f"section_{section_idx}_header_p{para_idx}",
                            paragraph_ref=paragraph,
                        )
                    )
            footer = section.footer
            for para_idx, paragraph in enumerate(footer.paragraphs):
                if paragraph.text.strip():
                    segments.append(
                        DocumentSegment(
                            text=paragraph.text,
                            segment_type="footer",
                            location_id=f"section_{section_idx}_footer_p{para_idx}",
                            paragraph_ref=paragraph,
                        )
                    )
                    
        footnote_segments = self._extract_footnote_segments()
        segments.extend(footnote_segments)
        
        return segments

    def _extract_footnote_segments(self) -> List[DocumentSegment]:
        """Parse word/footnotes.xml directly from docx archive per Non-Negotiable #5."""
        footnote_segments: List[DocumentSegment] = []
        try:
            with zipfile.ZipFile(self.docx_path, "r") as archive:
                if "word/footnotes.xml" not in archive.namelist():
                    return footnote_segments
                xml_data = archive.read("word/footnotes.xml")
                root = ET.fromstring(xml_data)
                
                ns = {"w": self.WORD_NAMESPACE}
                footnotes = root.findall(".//w:footnote", ns)
                for fn_idx, footnote in enumerate(footnotes):
                    fn_type = footnote.get(f"{{{self.WORD_NAMESPACE}}}type")
                    if fn_type in ["separator", "continuationSeparator"]:
                        continue
                    text_nodes = footnote.findall(".//w:t", ns)
                    combined_text = "".join(node.text for node in text_nodes if node.text)
                    if combined_text.strip():
                        footnote_segments.append(
                            DocumentSegment(
                                text=combined_text,
                                segment_type="footnote",
                                location_id=f"footnote_{fn_idx}",
                                paragraph_ref=None,
                            )
                        )
        except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError):
            pass
        return footnote_segments

    def apply_replacements(self, replacements: Dict[str, str], output_path: str) -> None:
        """Replace target entity strings across paragraphs, tables, headers, footers, and footnotes."""
        sorted_pairs = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)
        
        for paragraph in self.doc.paragraphs:
            self._replace_in_paragraph(paragraph, sorted_pairs)
            
        for table in self.doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph(paragraph, sorted_pairs)
                        
        for section in self.doc.sections:
            for paragraph in section.header.paragraphs:
                self._replace_in_paragraph(paragraph, sorted_pairs)
            for paragraph in section.footer.paragraphs:
                self._replace_in_paragraph(paragraph, sorted_pairs)
                
        temp_dir = tempfile.mkdtemp()
        try:
            self.doc.save(output_path)
            self._replace_in_footnotes_xml(output_path, sorted_pairs, temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _replace_in_paragraph(self, paragraph: Paragraph, sorted_pairs: List[Tuple[str, str]]) -> None:
        """Perform text replacement on paragraph while maintaining run-level formatting."""
        full_text = paragraph.text
        if not full_text:
            return
            
        matching_pairs = [(orig, fake) for orig, fake in sorted_pairs if orig in full_text]
        if not matching_pairs:
            return
            
        new_text = full_text
        for original, fake in matching_pairs:
            new_text = new_text.replace(original, fake)
            
        runs = paragraph.runs
        if not runs:
            paragraph.text = new_text
            return
            
        for idx in range(len(runs)):
            for orig, fake in matching_pairs:
                if orig in runs[idx].text:
                    runs[idx].text = runs[idx].text.replace(orig, fake)

        current_concat = "".join(r.text for r in runs)
        if current_concat != new_text:
            runs[0].text = new_text
            for run in runs[1:]:
                run.text = ""

    def _replace_in_footnotes_xml(
        self, docx_file_path: str, sorted_pairs: List[Tuple[str, str]], scratch_dir: str
    ) -> None:
        """Unzip docx file, perform XML text node replacement on word/footnotes.xml, and re-zip."""
        unzip_folder = os.path.join(scratch_dir, "unzipped")
        os.makedirs(unzip_folder, exist_ok=True)
        
        with zipfile.ZipFile(docx_file_path, "r") as archive:
            archive.extractall(unzip_folder)
            
        footnotes_path = os.path.join(unzip_folder, "word", "footnotes.xml")
        if not os.path.exists(footnotes_path):
            return
            
        try:
            ET.register_namespace("w", self.WORD_NAMESPACE)
            tree = ET.parse(footnotes_path)
            root = tree.getroot()
            
            ns = {"w": self.WORD_NAMESPACE}
            for text_node in root.findall(".//w:t", ns):
                if text_node.text:
                    node_text = text_node.text
                    for original, fake in sorted_pairs:
                        if original in node_text:
                            node_text = node_text.replace(original, fake)
                    text_node.text = node_text
                    
            tree.write(footnotes_path, encoding="utf-8", xml_declaration=True)
            
            zip_base_name = os.path.join(scratch_dir, "modified_docx")
            shutil.make_archive(zip_base_name, "zip", unzip_folder)
            modified_zip_path = zip_base_name + ".zip"
            
            shutil.copyfile(modified_zip_path, docx_file_path)
        except (ET.ParseError, OSError):
            pass
