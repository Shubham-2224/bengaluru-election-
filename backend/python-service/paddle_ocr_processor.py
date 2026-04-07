import os
import sys

# ADD CUSTOM PORTABLE PATH (FOR WINDOWS LONG PATH WORKAROUND)
if os.path.exists('C:\\p'):
    sys.path.append('C:\\p')

# Suppress PaddleOCR verbose output BEFORE import
os.environ['GLOG_minloglevel'] = '3'  # Suppress PaddlePaddle C++ logs
os.environ['FLAGS_print_model_net_proto'] = '0'
os.environ['PADDLEOCR_SHOW_LOG'] = '0'

import cv2
import numpy as np
from PIL import Image
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except Exception as e:
    PADDLE_AVAILABLE = False
    # print(f"WARNING: PaddleOCR import failed: {e}")

class PaddleOCRProcessor:
    """
    Wrapper for PaddleOCR to handle Marathi/Hindi text extraction
    with layout preservation.
    """
    
    def __init__(self, lang='mr'):
        """
        Initialize PaddleOCR
        Args:
            lang: Language code ('mr' for Marathi, 'hi' for Hindi, 'en' for English)
                 Note: 'mr' uses Devanagari models which also work for Hindi.
        """
        # PaddleOCR uses 'devanagari' type for both Marathi and Hindi in many versions,
        # but 'mr' and 'hi' are supported specific codes in v2.6+
        self.lang = lang
        self.ocr = None
        
        if PADDLE_AVAILABLE:
            try:
                # Initialize PaddleOCR
                # use_angle_cls=True to correct rotation
                # lang=self.lang to specify Marathi/Devanagari model
                # Silent initialization (verbose suppressed via environment variables)
                try:
                    self.ocr = PaddleOCR(
                        use_angle_cls=True, 
                        lang=self.lang, 
                        show_log=False,
                        use_gpu=False  # Use CPU for better compatibility
                    )
                except (TypeError, ValueError):
                    # Fallback if show_log not supported
                    self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, use_gpu=False)
            except Exception as e:
                print(f"Error initializing PaddleOCR: {str(e)}")
        else:
            print("PaddleOCR not available (Import failed).")

    def set_language(self, lang):
        """
        Switch OCR language at runtime
        """
        if lang == self.lang:
            return
            
        print(f"Switching PaddleOCR language to '{lang}'...")
        try:
            from paddleocr import PaddleOCR
            self.lang = lang
            try:
                self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
            except:
                self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang)
            print(f"PaddleOCR switched to '{lang}' successfully.")
        except Exception as e:
            print(f"Error switching PaddleOCR language: {str(e)}")

    def extract_text(self, image):
        """
        run OCR on an image (PIL or numpy)
        Returns:
            list of dicts: [{'text': str, 'confidence': float, 'box': list}]
        """
        if not self.ocr:
            return []

        # Convert PIL to numpy if needed
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # PaddleOCR expects BGR for cv2, but can handle RGB. 
        # Safest is to ensure it is standard numpy array.
        
        try:
            result = self.ocr.ocr(image, cls=True)
            
            # PaddleOCR returns a list of lists (one per page). We typically process single images.
            if not result or result[0] is None:
                return []
            
            # Flatten/Normalize output
            # result structure: [[[[x1,y1],[x2,y2]..], ("text", conf)], ...]
            
            parsed_results = []
            for line in result[0]:
                box = line[0]
                text, confidence = line[1]
                
                parsed_results.append({
                    'text': text,
                    'confidence': confidence,
                    'box': box
                })
                
            return parsed_results
            
        except Exception as e:
            print(f"PaddleOCR extraction error: {str(e)}")
            return []

    def get_full_text(self, image, separator="\n"):
        """
        Returns full extracted text joined by separator.
        Basic Layout logic: sort by Y then X to maintain reading order.
        """
        results = self.extract_text(image)
        if not results:
            return ""
            
        # Sort by vertical position (Y), then horizontal (X)
        # box[0][1] is top-left Y
        # box[0][0] is top-left X
        # We can add a tolerance for Y to group lines.
        
        # Simple sort:
        results.sort(key=lambda x: (x['box'][0][1], x['box'][0][0]))
        
        texts = [item['text'] for item in results]
        return separator.join(texts)

if __name__ == "__main__":
    if PADDLE_AVAILABLE:
        proc = PaddleOCRProcessor()
        print("PaddleOCR Processor ready.")
    else:
        print("PaddleOCR library missing.")
