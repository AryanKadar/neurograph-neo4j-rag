"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Document Parser
═══════════════════════════════════════════════════════════════
"""

import os
from typing import Optional
from config.settings import settings
import io
from utils.logger import setup_logger

logger = setup_logger()


class DocumentParser:
    """
    ┌─────────────────────────────────────────────┐
    │  📄 Parse various document formats          │
    │  Supports: PDF, DOCX, TXT, MD               │
    └─────────────────────────────────────────────┘
    """
    
    @staticmethod
    def parse(file_path: str) -> str:
        """
        Parse document and extract text
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        logger.info(f"📄 Parsing document: {os.path.basename(file_path)}")
        logger.info(f"   └─ Format: {ext}")
        
        if ext in ['.txt', '.md']:
            return DocumentParser._parse_text(file_path)
        elif ext == '.pdf':
            return DocumentParser._parse_pdf(file_path)
        elif ext == '.docx':
            return DocumentParser._parse_docx(file_path)
        else:
            raise ValueError(f"❌ Unsupported file format: {ext}")
    
    @staticmethod
    def _parse_text(file_path: str) -> str:
        """Parse plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        logger.info(f"   └─ Extracted: {len(content)} characters")
        return content
    
    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """Parse PDF file"""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(file_path)
            text_parts = []
            
            logger.info(f"   └─ Pages found: {len(reader.pages)}")
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text)
                    logger.info(f"      └─ Page {page_num + 1}: {len(text)} chars")
                
                # 🖼️ MULTIMODAL EXTRACTION
                if settings.ENABLE_MULTIMODAL:
                    try:
                        # Try to import dependencies locally to avoid crash if missing
                        import ollama
                        from PIL import Image
                        
                        if hasattr(page, 'images') and page.images:
                            logger.info(f"      └─ Found {len(page.images)} images on page {page_num + 1}")
                            
                            for img_obj in page.images:
                                try:
                                    # Convert bytes to PIL Image (validation)
                                    image_bytes = img_obj.data
                                    
                                    # Call Ollama Vision (Llama 3.2 Vision)
                                    # Note: This adds latency but enriches content significantly
                                    response = ollama.chat(
                                        model=settings.OLLAMA_VISION_MODEL,
                                        messages=[{
                                            'role': 'user',
                                            'content': 'Describe this image in detail. If it is a chart or graph, summarize the data points and trends. If it is a diagram, explain the flow.',
                                            'images': [image_bytes]
                                        }]
                                    )
                                    
                                    description = response['message']['content']
                                    desc_marker = f"\n\n[IMAGE DESCRIPTION: {description}]\n\n"
                                    text_parts.append(desc_marker)
                                    logger.info(f"         └─ Generated description: {description[:50]}...")
                                    
                                except Exception as img_err:
                                    logger.warning(f"         ⚠️ Failed to process image: {img_err}")
                                    
                    except ImportError:
                        logger.warning("      ⚠️ Multimodal dependencies (ollama, pillow) missing. Skipping images.")
                    except Exception as mm_err:
                        logger.warning(f"      ⚠️ Multimodal processing error: {mm_err}")
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"   └─ Total extracted: {len(full_text)} characters")
            
            return full_text
            
        except Exception as e:
            logger.error(f"❌ PDF parsing error: {e}")
            raise
    
    @staticmethod
    def _parse_docx(file_path: str) -> str:
        """Parse DOCX file"""
        try:
            from docx import Document as DocxDocument
            
            doc = DocxDocument(file_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            full_text = "\n\n".join(paragraphs)
            
            logger.info(f"   └─ Paragraphs: {len(paragraphs)}")
            logger.info(f"   └─ Total extracted: {len(full_text)} characters")
            
            return full_text
            
        except Exception as e:
            logger.error(f"❌ DOCX parsing error: {e}")
            raise
