"""
PDF Extraction Module for Lab Reports
Extracts lab test names, values, and ranges from uploaded PDF files
"""

import pdfplumber
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class LabResult:
    """Represents a single lab test result"""
    test_name: str
    value: str
    unit: str
    reference_range: str
    status: str  # 'normal', 'high', 'low', 'unknown'

class LabReportExtractor:
    """Extract structured data from lab report PDFs"""
    
    def __init__(self):
        # Common lab test patterns
        self.test_patterns = [
            r'(Hemoglobin|Hgb|Hb)\s*:?\s*([\d.]+)\s*([a-zA-Z/]+)?\s*(?:Ref\.?\s*Range:?\s*)?([\d.\-\s]+)',
            r'(WBC|White Blood Cell|Leukocyte)\s*:?\s*([\d.]+)\s*([a-zA-Z/]+)?\s*(?:Ref\.?\s*Range:?\s*)?([\d.\-\s]+)',
            r'(Glucose|Blood Sugar)\s*:?\s*([\d.]+)\s*([a-zA-Z/]+)?\s*(?:Ref\.?\s*Range:?\s*)?([\d.\-\s]+)',
            r'(Iron|Ferritin)\s*:?\s*([\d.]+)\s*([a-zA-Z/]+)?\s*(?:Ref\.?\s*Range:?\s*)?([\d.\-\s]+)',
            r'(Cholesterol|LDL|HDL)\s*:?\s*([\d.]+)\s*([a-zA-Z/]+)?\s*(?:Ref\.?\s*Range:?\s*)?([\d.\-\s]+)',
        ]
    
    def extract_from_pdf(self, pdf_path: str) -> List[LabResult]:
        """Extract lab results from PDF file"""
        results = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                
                # Try to extract tables first (more structured)
                tables = page.extract_tables()
                if tables:
                    results.extend(self._parse_tables(tables))
                
                # Fall back to pattern matching
                results.extend(self._parse_text(text))
        
        # Remove duplicates
        unique_results = self._deduplicate_results(results)
        
        return unique_results
    
    def _parse_tables(self, tables: List) -> List[LabResult]:
        """Parse lab results from extracted tables"""
        results = []
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Assume first row is header
            headers = [h.lower() if h else '' for h in table[0]]
            
            # Find relevant columns
            test_col = self._find_column(headers, ['test', 'name', 'component'])
            value_col = self._find_column(headers, ['value', 'result'])
            unit_col = self._find_column(headers, ['unit', 'units'])
            range_col = self._find_column(headers, ['range', 'reference', 'normal'])
            
            # Parse data rows
            for row in table[1:]:
                if not row or len(row) <= max(test_col or 0, value_col or 0):
                    continue
                
                test_name = row[test_col] if test_col is not None else ''
                value = row[value_col] if value_col is not None else ''
                unit = row[unit_col] if unit_col is not None else ''
                ref_range = row[range_col] if range_col is not None else ''
                
                if test_name and value:
                    status = self._determine_status(value, ref_range)
                    results.append(LabResult(
                        test_name=test_name.strip(),
                        value=str(value).strip(),
                        unit=str(unit).strip() if unit else '',
                        reference_range=str(ref_range).strip() if ref_range else '',
                        status=status
                    ))
        
        return results
    
    def _parse_text(self, text: str) -> List[LabResult]:
        """Parse lab results using regex patterns"""
        results = []
        
        for pattern in self.test_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    test_name = groups[0]
                    value = groups[1]
                    unit = groups[2] if len(groups) > 2 else ''
                    ref_range = groups[3] if len(groups) > 3 else ''
                    
                    status = self._determine_status(value, ref_range)
                    results.append(LabResult(
                        test_name=test_name,
                        value=value,
                        unit=unit or '',
                        reference_range=ref_range or '',
                        status=status
                    ))
        
        return results
    
    def _find_column(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by keywords"""
        for i, header in enumerate(headers):
            for keyword in keywords:
                if keyword in header:
                    return i
        return None
    
    def _determine_status(self, value: str, ref_range: str) -> str:
        """Determine if value is normal, high, or low"""
        try:
            val = float(value.replace(',', ''))
            
            # Parse reference range
            range_match = re.search(r'([\d.]+)\s*-\s*([\d.]+)', ref_range)
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                
                if val < low:
                    return 'low'
                elif val > high:
                    return 'high'
                else:
                    return 'normal'
        except (ValueError, AttributeError):
            pass
        
        return 'unknown'
    
    def _deduplicate_results(self, results: List[LabResult]) -> List[LabResult]:
        """Remove duplicate test results"""
        seen = set()
        unique = []
        
        for result in results:
            key = (result.test_name.lower(), result.value)
            if key not in seen:
                seen.add(key)
                unique.append(result)
        
        return unique

# Example usage
if __name__ == "__main__":
    extractor = LabReportExtractor()
    results = extractor.extract_from_pdf("sample_lab_report.pdf")
    
    for result in results:
        print(f"{result.test_name}: {result.value} {result.unit} [{result.status}]")
        print(f"  Reference: {result.reference_range}")