#!/usr/bin/env python3
"""
PDF Filler using pikepdf - Preserves embedded fonts and existing appearances in the template
Based on ChatGPT's recommended approach: reuse existing appearances instead of creating new ones
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pikepdf
from pikepdf import Pdf, Object, Name, String, Dictionary, Array


# ----------------------------- Helpers -----------------------------

TRUTHY = {"1", "true", "on", "yes", "y", "t"}

def str_to_bool(v) -> bool:
    """Convert value to boolean"""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in TRUTHY

def ensure_name(n: str) -> Name:
    """Ensure a value is a valid PDF Name object (must start with '/')"""
    n = (n or "").strip()
    if not n:
        return Name("/Off")
    return Name("/" + n.lstrip("/"))

def is_radio(field_dict) -> bool:
    """Check if field is a radio button"""
    ff = int(field_dict.get("/Ff", 0) or 0)
    # PDF spec: button field flag bit 15 (0x8000) indicates Radio
    return (ff & 0x8000) != 0

def collect_fields(root_fields) -> Dict[str, dict]:
    """Build a map of full field name -> field dict"""
    result = {}
    
    def walk(field, prefix=""):
        fname_obj = field.get("/T")
        fname = str(fname_obj) if fname_obj is not None else None
        ft = field.get("/FT")
        full = f"{prefix}.{fname}" if prefix and fname else (fname or prefix)
        
        kids = field.get("/Kids")
        if ft is not None:
            # Terminal field (has /FT)
            if full:
                result[full] = field
        
        if kids:
            # Recurse into kids with updated prefix (hierarchical names)
            next_prefix = full or prefix
            for kid in kids:
                walk(kid, next_prefix)
    
    for f in root_fields:
        walk(f, "")
    
    return result

def widgets_for_field(pdf: Pdf, field: dict) -> List[dict]:
    """
    Find widget annotations belonging to a field by scanning page /Annots.
    Most robust way, since widgets often live on pages with /Parent pointing to the field.
    """
    widgets = []
    
    for page in pdf.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        
        for annot in annots:
            try:
                if annot.get("/Subtype") != Name("/Widget"):
                    continue
                
                parent = annot.get("/Parent")
                # Some PDFs put /T on the widget, but /Parent is the safest link
                if parent is field:
                    widgets.append(annot)
            except Exception:
                continue
    
    # Fallback: some forms place widgets directly as kids of the field
    if not widgets:
        kids = field.get("/Kids")
        if kids:
            for kid in kids:
                try:
                    if kid.get("/Subtype") == Name("/Widget"):
                        widgets.append(kid)
                except Exception:
                    continue
    
    return widgets

def widget_on_state_names(annot: dict) -> List[Name]:
    """
    Return the list of valid 'on' appearance names for this widget by
    reading /AP /N keys and excluding /Off.
    """
    ap = annot.get("/AP")
    if not ap:
        return []
    
    apN = ap.get("/N")
    if not apN:
        return []
    
    try:
        keys = list(apN.keys())
    except Exception:
        # Some PDFs store a single stream instead of a dict; no named keys then.
        return []
    
    return [k for k in keys if k != Name("/Off")]

def choose_radio_widget_by_value(widgets: List[dict], value: str) -> Tuple[Optional[dict], Optional[Name]]:
    """
    For radios: pick the widget whose /AP /N has a key matching the provided value.
    Matching is case-insensitive and ignores the leading slash.
    Returns (widget, /Name) or (None, None) if not found.
    """
    if value is None:
        return None, None
    
    target = str(value).strip().lower().lstrip("/")
    
    for w in widgets:
        for k in widget_on_state_names(w):
            if str(k)[1:].lower() == target:
                return w, k
    
    return None, None

def first_on_state(widgets: List[dict]) -> Optional[Name]:
    """For checkboxes: pick the first available on-state from the first widget."""
    for w in widgets:
        ons = widget_on_state_names(w)
        if ons:
            return ons[0]
    return None


# ----------------------------- Core filling -----------------------------

def fill_pdf_with_pikepdf(template_path, output_path, fields, options=None):
    """
    Fill PDF form fields using pikepdf
    Preserves embedded fonts and existing appearances in the template
    
    Args:
        template_path: Path to template PDF
        output_path: Path to output PDF
        fields: Dictionary of field_name -> value
        options: Dictionary with options (currently unused)
    
    Returns:
        Dictionary with success status and metadata
    """
    if options is None:
        options = {}
    
    print(f"📝 Opening template: {template_path}")
    pdf = Pdf.open(template_path)
    
    acro = pdf.Root.get("/AcroForm")
    if not acro:
        print("⚠️  Template PDF has no AcroForm. Cannot fill fields.")
        pdf.save(output_path)
        pdf.close()
        return {'success': False, 'error': 'No AcroForm found'}
    
    root_fields = acro.get("/Fields", [])
    field_map = collect_fields(root_fields)
    
    print(f"📋 Found {len(field_map)} form fields")
    
    filled = 0
    skipped = []
    
    # We do NOT set /NeedAppearances; we rely on the template's appearances and fonts.
    # If you ever need it: acro["/NeedAppearances"] = False
    
    for raw_name, value in fields.items():
        if value is None or value == '':
            continue
        
        # exact, else case-insensitive match
        field_name = raw_name
        field_dict = field_map.get(field_name)
        
        if not field_dict:
            low = field_name.lower()
            for k, v in field_map.items():
                if str(k).lower() == low:
                    field_name, field_dict = k, v
                    break
        
        if not field_dict:
            skipped.append(raw_name)
            continue
        
        ft = field_dict.get("/FT")
        
        if ft == Name("/Tx"):
            # Text: set /V to a PDF String; embedded font in template handles JP
            field_dict["/V"] = String("" if value is None else str(value))
            filled += 1
            continue
        
        if ft == Name("/Btn"):
            widgets = widgets_for_field(pdf, field_dict)
            
            if not widgets:
                skipped.append(raw_name)
                continue
            
            if is_radio(field_dict):
                # Radio group: pick widget that matches provided value
                widget, on_name = choose_radio_widget_by_value(widgets, str(value) if value is not None else "")
                
                if widget and on_name:
                    field_dict["/V"] = on_name
                    # set selected widget to on_name, others to /Off
                    for ww in widgets:
                        ww["/AS"] = on_name if ww is widget else Name("/Off")
                    filled += 1
                else:
                    skipped.append(raw_name)
                continue
            
            # Checkbox
            on_state = first_on_state(widgets) or Name("/Yes")
            
            if str_to_bool(value):
                field_dict["/V"] = on_state
                for ww in widgets:
                    ww["/AS"] = on_state
            else:
                field_dict["/V"] = Name("/Off")
                for ww in widgets:
                    ww["/AS"] = Name("/Off")
            
            filled += 1
            continue
        
        # Other field types (choice etc.) — basic /V set
        field_dict["/V"] = String("" if value is None else str(value))
        filled += 1
    
    print(f"✅ Filled {filled} fields (skipped {len(skipped)})")
    
    # Save output
    print(f"💾 Saving to: {output_path}")
    pdf.save(output_path, compress_streams=True)
    pdf.close()
    
    output_size = Path(output_path).stat().st_size
    print(f"✅ PDF created successfully ({output_size} bytes)")
    
    return {
        'success': True,
        'filled_count': filled,
        'skipped_count': len(skipped),
        'skipped_fields': skipped,
        'total_fields': len(field_map),
        'output_size': output_size
    }


def main():
    parser = argparse.ArgumentParser(description='Fill PDF form using pikepdf - preserves template appearances')
    parser.add_argument('template_path', help='Path to template PDF')
    parser.add_argument('output_path', help='Path to output PDF')
    parser.add_argument('--fields', required=True, help='JSON string of field_name:value pairs')
    parser.add_argument('--regenerate-appearances', action='store_true', default=False,
                        help='[Deprecated] Not used - we reuse template appearances')
    parser.add_argument('--no-regenerate-appearances', dest='regenerate_appearances', action='store_false',
                        help='[Deprecated] Not used - we reuse template appearances')
    parser.add_argument('--flatten', action='store_true', default=False,
                        help='Flatten PDF (remove form fields)')
    
    args = parser.parse_args()
    
    # Parse fields JSON
    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing fields JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Fill PDF
    options = {
        'regenerate_appearances': False,  # We don't regenerate - we reuse template appearances
        'flatten': args.flatten
    }
    
    result = fill_pdf_with_pikepdf(args.template_path, args.output_path, fields, options)
    
    # Output result as JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
